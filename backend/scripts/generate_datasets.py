import os
import sys
import uuid
import random
import logging
from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import SessionLocal
from models.asset import Transformer, Substation, Feeder
from services.ai_service import ai_service

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DatasetGenerator")

def generate_all_datasets():
    db = SessionLocal()
    try:
        # Create output directories
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
        os.makedirs(data_dir, exist_ok=True)
        logger.info(f"Ensuring data directory exists at: {data_dir}")

        db_loaded = False
        try:
            transformers = db.query(Transformer).all()
            if transformers:
                db_loaded = True
        except Exception as e:
            logger.warning(f"Database connection failed, skipping database query: {e}")
            transformers = []
            
        if not transformers:
            seed_path = os.path.join(data_dir, "seed_transformers.csv")
            if os.path.exists(seed_path):
                logger.info(f"Loading mock transformers from {seed_path} to generate telemetry and trends...")
                class MockTransformer:
                    def __init__(self, row):
                        self.id = row["transformer_id"]
                        self.transformer_code = row["transformer_code"]
                        self.rated_kva = float(row["rated_kva"]) if pd.notna(row["rated_kva"]) else 500.0
                        self.age_years = float(row["age_years"]) if pd.notna(row["age_years"]) else 10.0
                        self.current_failure_risk = float(row["current_failure_risk"]) if pd.notna(row["current_failure_risk"]) else 0.1
                        self.current_status = str(row["current_status"]) if pd.notna(row["current_status"]) else "healthy"
                        self.latitude = float(row["latitude"]) if pd.notna(row["latitude"]) else 26.14
                        self.longitude = float(row["longitude"]) if pd.notna(row["longitude"]) else 91.74
                        self.location = None
                try:
                    seed_df = pd.read_csv(seed_path)
                    # Limit mock transformers to top 100 to keep execution fast and prevent API block
                    mock_subset = seed_df.head(100)
                    transformers = [MockTransformer(row) for _, row in mock_subset.iterrows()]
                except Exception as ex:
                    logger.error(f"Failed to load mock transformers from seed CSV: {ex}")
            else:
                logger.warning("No seed_transformers.csv found. Proceeding with ML dataset generation only.")

        # ==========================================
        # 1. Generate telemetry_history.csv
        # ==========================================
        if transformers:
            logger.info("Generating telemetry_history.csv...")
        now = datetime.now(timezone.utc)
        telemetry_rows = []

        for idx, t in enumerate(transformers):
            # Coordinates for weather check
            lat = 26.14
            lon = 91.74
            if hasattr(t, "latitude") and hasattr(t, "longitude"):
                lat = float(t.latitude)
                lon = float(t.longitude)
            else:
                try:
                    from geoalchemy2.shape import to_shape
                    if t.location:
                        point = to_shape(t.location)
                        lat = float(point.y)
                        lon = float(point.x)
                except Exception:
                    pass
            ambient_temp = ai_service._fetch_live_weather(lat, lon)

            # Deterministic status profile based on transformer ID to avoid DB dependency
            status_random = random.Random(str(t.id))
            rand_val = status_random.random()
            is_critical = (rand_val < 0.05)
            is_warning = (0.05 <= rand_val < 0.15)

            for h in range(24):
                time_pt = now - timedelta(hours=(23 - h))
                hour = time_pt.hour

                # Deterministic seed using transformer ID and hour to make it reproducible
                seed_str = f"{t.id}_{time_pt.strftime('%Y%m%d%H')}"
                local_random = random.Random(seed_str)

                rated_kva = float(t.rated_kva) if t.rated_kva else 500.0
                age_years = int(t.age_years) if t.age_years else 10

                if is_critical:
                    load = local_random.uniform(110, 140)
                    voltage = 415.0 - (load / 100.0) * 55.0 + local_random.uniform(-3, 3)
                    temp = ambient_temp + (load / 100.0)**2 * 45.0 + age_years * 1.2 + local_random.uniform(-2, 2)
                elif is_warning:
                    load = local_random.uniform(80, 105)
                    voltage = 415.0 - (load / 100.0) * 35.0 + local_random.uniform(-3, 3)
                    temp = ambient_temp + (load / 100.0)**2 * 35.0 + age_years * 0.8 + local_random.uniform(-2, 2)
                else:
                    load_base = local_random.uniform(30, 60)
                    if 18 <= hour <= 22:
                        load = load_base + local_random.uniform(15, 25)
                    else:
                        load = load_base + local_random.uniform(-5, 5)
                    voltage = 415.0 - (load / 100.0) * 15.0 + local_random.uniform(-2, 2)
                    temp_offset = local_random.uniform(5, 12) if 11 <= hour <= 16 else local_random.uniform(0, 4)
                    temp = ambient_temp + temp_offset + (load / 100.0)**2 * 20.0 + age_years * 0.5 + local_random.uniform(-1, 1)

                current = (rated_kva * 1000.0 * (load / 100.0)) / (1.732 * voltage) + local_random.uniform(-2, 2)

                telemetry_rows.append({
                    "transformer_id": str(t.id),
                    "transformer_code": t.transformer_code,
                    "timestamp": time_pt.isoformat(),
                    "load_percentage": round(load, 2),
                    "voltage_lv": round(voltage, 1),
                    "current_a": round(current, 1),
                    "temperature_c": round(temp, 1)
                })

            if (idx + 1) % 500 == 0:
                logger.info(f"Generated telemetry for {idx + 1}/{len(transformers)} transformers...")

        telemetry_df = pd.DataFrame(telemetry_rows)
        telemetry_path = os.path.join(data_dir, "telemetry_history.csv")
        telemetry_df.to_csv(telemetry_path, index=False)
        logger.info(f"Saved {len(telemetry_df)} rows to {telemetry_path}")

        # ==========================================
        # 2. Generate health_trend_history.csv
        # ==========================================
        logger.info("Generating health_trend_history.csv...")
        trend_rows = []

        for idx, t in enumerate(transformers):
            current_anomaly = float(t.current_failure_risk * 100.0) if t.current_failure_risk is not None else 15.0
            
            # Seed with transformer ID to keep it stable
            local_random = random.Random(str(t.id))

            for i in range(7):
                day = now - timedelta(days=6 - i)
                variance = local_random.uniform(-4.0, 4.0)
                day_anomaly = max(5.0, min(98.0, current_anomaly + (6 - i) * local_random.uniform(-1.5, 0.5) + variance))
                if i == 6:
                    day_anomaly = current_anomaly

                trend_rows.append({
                    "transformer_id": str(t.id),
                    "timestamp": day.date().isoformat(),
                    "anomaly_score": round(day_anomaly, 2),
                    "health_score": int(100 - day_anomaly)
                })

        trend_df = pd.DataFrame(trend_rows)
        trend_path = os.path.join(data_dir, "health_trend_history.csv")
        trend_df.to_csv(trend_path, index=False)
        logger.info(f"Saved {len(trend_df)} rows to {trend_path}")

        # ==========================================
        # 3. Generate ml_training_dataset.csv (Forward Physics-Based Generation)
        # ==========================================
        logger.info("Generating ml_training_dataset.csv (10,000 samples)...")
        np.random.seed(42)
        n_samples = 10000

        # APDCL standard transformer capacities
        kva_options = [25, 63, 100, 250, 315, 500]
        
        # Independent features
        base_kva = np.random.choice(kva_options, n_samples)
        # Age mostly between 6-15 years
        base_age = np.clip(np.random.normal(10.5, 4.0, n_samples), 1, 25)
        # Ambient temperature (continuous)
        base_ambient = np.random.normal(29.0, 4.0, n_samples)
        
        # Load profile mixture to simulate healthy (majority) and stressed (minority) transformers
        load_normal = np.random.normal(55, 15, int(n_samples * 0.75))
        load_high = np.random.normal(85, 8, int(n_samples * 0.15))
        load_over = np.random.normal(115, 15, int(n_samples * 0.10))
        base_load = np.concatenate([load_normal, load_high, load_over])
        np.random.shuffle(base_load)
        base_load = np.clip(base_load, 10.0, 150.0)
        
        # Dynamic Power Factor (depends on load)
        power_factor = 0.82 + (base_load / 150.0) * 0.16 + np.random.normal(0, 0.01, n_samples)
        power_factor = np.clip(power_factor, 0.80, 0.98)
        
        # Physics-based dependent calculations
        # Rated current
        rated_current = (base_kva * 1000.0) / (1.732 * 415.0)
        
        # 1. Voltage Drop (depends on current & impedance)
        # Z_ohms = 4.5% impedance = 0.045 * (415.0 / rated_current)
        typical_impedance_ohms = 0.045 * (415.0 / rated_current)
        
        # Generate initial current approximation based on load
        approx_current = rated_current * (base_load / 100.0)
        voltage_drop = approx_current * typical_impedance_ohms
        base_voltage = 415.0 - voltage_drop + np.random.normal(0, 1.5, n_samples)
        
        # 2. Current Formula
        base_current = (base_kva * 1000.0 * (base_load / 100.0)) / (1.732 * base_voltage * power_factor) + np.random.normal(0, 2.0, n_samples)
        # Clip current to max 1.5x rated current (breaker limit)
        base_current = np.clip(base_current, 0, 1.5 * rated_current)
        
        # 3. Temperature (I^2R heating)
        max_temp_rise = 45.0
        aging_factor = base_age * 0.4
        base_temp = base_ambient + (base_current / rated_current)**2 * max_temp_rise + aging_factor + np.random.normal(0, 1.5, n_samples)
        
        # Health Engine (Vectorized, physics-inspired penalties)
        temp_penalty = (np.maximum(0.0, base_temp - 70.0) / 15.0) ** 2 * 12.0
        load_penalty = (np.maximum(0.0, base_load - 80.0) / 20.0) ** 2 * 10.0
        voltage_penalty = (np.abs(base_voltage - 415.0) / 20.0) ** 2 * 8.0
        current_penalty = np.maximum(0.0, (base_current / rated_current) - 1.0) * 25.0
        age_penalty = (base_age / 25.0) ** 1.8 * 12.0
        
        health = 100.0 - temp_penalty - load_penalty - voltage_penalty - current_penalty - age_penalty
        health = np.clip(health, 0, 100)
        
        # Failure probability mapping (Sigmoid instead of linear)
        failure_prob = 100.0 / (1.0 + np.exp(0.08 * (health - 45.0)))
        
        # Label generation directly from health score
        labels = np.select(
            [health >= 75.0, health >= 45.0],
            [0, 1],
            default=2
        )
        
        # Feature Engineering columns
        load_ratio = base_load / 100.0
        current_ratio = base_current / rated_current
        voltage_deviation = (415.0 - base_voltage) / 415.0
        temperature_rise = base_temp - base_ambient
        # Stress index increases with age
        stress_index = current_ratio * temperature_rise * (1.0 + 0.05 * base_age)
        
        train_df = pd.DataFrame({
            "temperature_c":       np.round(base_temp, 2),
            "load_percentage":     np.round(base_load, 2),
            "voltage_lv":          np.round(base_voltage, 1),
            "current_a":           np.round(base_current, 1),
            "ambient_temperature": np.round(base_ambient, 1),
            "age_years":           np.round(base_age, 1),
            "rated_kva":           base_kva,
            "power_factor":        np.round(power_factor, 2),
            "load_ratio":          np.round(load_ratio, 3),
            "current_ratio":       np.round(current_ratio, 3),
            "voltage_deviation":   np.round(voltage_deviation, 3),
            "temperature_rise":    np.round(temperature_rise, 2),
            "stress_index":        np.round(stress_index, 3),
            "health_score":        np.round(health, 1),
            "failure_probability": np.round(failure_prob, 1),
            "risk_label":          labels
        })

        train_path = os.path.join(data_dir, "ml_training_dataset.csv")
        train_df.to_csv(train_path, index=False)
        label_counts = train_df['risk_label'].value_counts().sort_index()
        logger.info(f"Saved {len(train_df)} rows of training data: SAFE={label_counts.get(0,0)}, WARNING={label_counts.get(1,0)}, CRITICAL={label_counts.get(2,0)}")

        # ==========================================
        # 4. Generate seed_transformers.csv (Baseline Database Snapshot)
        # ==========================================
        if transformers and db_loaded:
            logger.info("Generating seed_transformers.csv...")
            seed_rows = []
    
            # Cache substations and feeders to prevent 3300+ database round-trips
            substations_cache = {s.id: s for s in db.query(Substation).all()}
            feeders_cache = {f.id: f for f in db.query(Feeder).all()}

            for idx, t in enumerate(transformers):
                # Extract longitude/latitude from PostGIS Geography
                lon, lat = 91.74, 26.14
                try:
                    from geoalchemy2.shape import to_shape
                    if t.location:
                        point = to_shape(t.location)
                        lon, lat = float(point.x), float(point.y)
                except Exception:
                    pass
    
                sub = substations_cache.get(t.substation_id)
                fd = feeders_cache.get(t.feeder_id)
    
                seed_rows.append({
                    "transformer_id": str(t.id),
                    "transformer_code": t.transformer_code,
                    "substation_code": sub.code if sub else "SS_133",
                    "substation_name": sub.name if sub else "Unknown Substation",
                    "feeder_code": fd.code if fd else "FD_UNKNOWN",
                    "feeder_name": fd.name if fd else "Unknown Feeder",
                    "rated_kva": float(t.rated_kva),
                    "age_years": int(t.age_years or 10),
                    "is_metered": bool(t.is_metered),
                    "current_load_pct": float(t.current_load_pct or 50.0),
                    "current_oil_temp_c": float(t.current_oil_temp_c or 45.0),
                    "current_health_score": int(t.current_health_score or 90),
                    "current_failure_risk": float(t.current_failure_risk or 0.1),
                    "current_status": t.current_status or "healthy",
                    "longitude": lon,
                    "latitude": lat,
                    "num_consumers": int(t.num_consumers or 50),
                    "manufacturer": t.manufacturer or "BHEL",
                    "cooling_type": t.cooling_type or "ONAN",
                    "installation_date": t.installation_date.isoformat() if t.installation_date else "2015-01-01",
                    "is_flood_prone": bool(t.is_flood_prone),
                    "is_high_lightning": bool(t.is_high_lightning),
                    "address_text": t.address_text or "",
                    "district": t.district or "Cachar",
                    "operational_status": t.operational_status or "IN_SERVICE"
                })
    
            seed_df = pd.DataFrame(seed_rows)
            seed_path = os.path.join(data_dir, "seed_transformers.csv")
            seed_df.to_csv(seed_path, index=False)
            logger.info(f"Saved {len(seed_df)} transformer records to {seed_path}")

        # ==========================================
        # 5. Generate lstm_training_data.npz
        # ==========================================
        logger.info("Generating lstm_training_data.npz...")
        n_sequences = 2000
        np.random.seed(42)
        X_seqs, y_seqs = [], []

        for _ in range(n_sequences):
            is_anomalous = np.random.random() < 0.2
            if is_anomalous:
                base_temp = np.random.uniform(80, 100)
                base_load = np.random.uniform(90, 130)
            else:
                base_temp = np.random.uniform(35, 65)
                base_load = np.random.uniform(25, 75)

            base_volt = np.random.uniform(395, 425)
            base_curr = np.random.uniform(40, 200)

            hours = np.arange(48)
            peak_factor = np.where((hours % 24 >= 18) & (hours % 24 <= 22), 1.15, 1.0)

            temp = base_temp + np.random.normal(0, 2, 48) + (3.0 * (((hours%24)>=12) & ((hours%24)<=16)))
            load = np.clip(base_load * peak_factor + np.random.normal(0, 3, 48), 0, 150)
            voltage = base_volt + np.random.normal(0, 3, 48)
            current = base_curr * peak_factor + np.random.normal(0, 8, 48)

            seq_in = np.column_stack([temp[:24], load[:24], voltage[:24], current[:24]])
            seq_out = np.column_stack([load[24:], temp[24:]])

            X_seqs.append(seq_in)
            y_seqs.append(seq_out)

        X_np = np.array(X_seqs, dtype=np.float32)
        y_np = np.array(y_seqs, dtype=np.float32)
        lstm_path = os.path.join(data_dir, "lstm_training_data.npz")
        np.savez_compressed(lstm_path, X=X_np, y=y_np)
        logger.info(f"Saved {n_sequences} sequences to {lstm_path}")

        logger.info("All static datasets generated successfully!")

    finally:
        db.close()

if __name__ == "__main__":
    generate_all_datasets()
