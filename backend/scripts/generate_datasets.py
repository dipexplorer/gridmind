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

        transformers = db.query(Transformer).all()
        if not transformers:
            logger.error("No transformers found in database. Seed data first.")
            return

        logger.info(f"Loaded {len(transformers)} transformers from database.")

        # ==========================================
        # 1. Generate telemetry_history.csv
        # ==========================================
        logger.info("Generating telemetry_history.csv...")
        now = datetime.now(timezone.utc)
        telemetry_rows = []

        for idx, t in enumerate(transformers):
            # Coordinates for weather check
            lat = 26.14
            lon = 91.74
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
        # 3. Generate ml_training_dataset.csv (Stratified — realistic operational distribution)
        # ==========================================
        logger.info("Generating ml_training_dataset.csv (10,000 samples)...")
        np.random.seed(42)

        # Stratified sampling to match real-world fleet distribution:
        # 70% healthy, 15% warning, 15% critical
        n_safe     = 7000
        n_warning  = 1500
        n_critical = 1500

        # Stratified sampling to match real-world fleet distribution:
        # 70% healthy, 15% warning, 15% critical
        n_safe     = 7000
        n_warning  = 1500
        n_critical = 1500

        # Helper distributions for metadata
        kva_options = [100, 250, 500, 1000]
        age_options = [1, 2, 3, 5, 8, 10, 12, 15, 20, 25]
        ambient_options = [15.0, 20.0, 25.0, 30.0, 35.0, 40.0]

        # --- HEALTHY ---
        safe_kva = np.random.choice(kva_options, n_safe)
        safe_age = np.random.choice(age_options, n_safe)
        safe_ambient = np.random.choice(ambient_options, n_safe)
        safe_load = np.random.uniform(20.0, 75.0, n_safe)
        safe_voltage = 415.0 - (safe_load / 100.0) * 15.0 + np.random.uniform(-2, 2, n_safe)
        safe_current = (safe_kva * 1000.0 * (safe_load / 100.0)) / (1.732 * safe_voltage) + np.random.uniform(-2, 2, n_safe)
        safe_temp = safe_ambient + (safe_load / 100.0)**2 * 20.0 + safe_age * 0.5 + np.random.uniform(-1, 1, n_safe)
        safe_labels = np.zeros(n_safe, dtype=int)

        # --- WARNING ---
        warn_kva = np.random.choice(kva_options, n_warning)
        warn_age = np.random.choice(age_options, n_warning)
        warn_ambient = np.random.choice(ambient_options, n_warning)
        warn_load = np.random.uniform(80.0, 105.0, n_warning)
        warn_voltage = 415.0 - (warn_load / 100.0) * 35.0 + np.random.uniform(-3, 3, n_warning)
        warn_current = (warn_kva * 1000.0 * (warn_load / 100.0)) / (1.732 * warn_voltage) + np.random.uniform(-3, 3, n_warning)
        warn_temp = warn_ambient + (warn_load / 100.0)**2 * 35.0 + warn_age * 0.8 + np.random.uniform(-2, 2, n_warning)
        warn_labels = np.ones(n_warning, dtype=int)

        # --- CRITICAL ---
        crit_kva = np.random.choice(kva_options, n_critical)
        crit_age = np.random.choice(age_options, n_critical)
        crit_ambient = np.random.choice(ambient_options, n_critical)
        crit_load = np.random.uniform(110.0, 140.0, n_critical)
        crit_voltage = 415.0 - (crit_load / 100.0) * 55.0 + np.random.uniform(-3, 3, n_critical)
        crit_current = (crit_kva * 1000.0 * (crit_load / 100.0)) / (1.732 * crit_voltage) + np.random.uniform(-3, 3, n_critical)
        crit_temp = crit_ambient + (crit_load / 100.0)**2 * 45.0 + crit_age * 1.2 + np.random.uniform(-2, 2, n_critical)
        crit_labels = np.full(n_critical, 2, dtype=int)

        # Stack all classes together and shuffle
        all_temp    = np.concatenate([safe_temp,    warn_temp,    crit_temp])
        all_load    = np.concatenate([safe_load,    warn_load,    crit_load])
        all_voltage = np.concatenate([safe_voltage, warn_voltage, crit_voltage])
        all_current = np.concatenate([safe_current, warn_current, crit_current])
        all_ambient = np.concatenate([safe_ambient, warn_ambient, crit_ambient])
        all_age     = np.concatenate([safe_age,     warn_age,     crit_age])
        all_kva     = np.concatenate([safe_kva,     warn_kva,     crit_kva])
        all_labels  = np.concatenate([safe_labels,  warn_labels,  crit_labels])

        shuffle_idx = np.random.permutation(len(all_labels))

        train_df = pd.DataFrame({
            "temperature_c":       np.round(all_temp[shuffle_idx], 2),
            "load_percentage":     np.round(all_load[shuffle_idx], 2),
            "voltage_lv":          np.round(all_voltage[shuffle_idx], 1),
            "current_a":           np.round(all_current[shuffle_idx], 1),
            "ambient_temperature": np.round(all_ambient[shuffle_idx], 1),
            "age_years":           all_age[shuffle_idx],
            "rated_kva":           all_kva[shuffle_idx],
            "risk_label":          all_labels[shuffle_idx]
        })

        train_path = os.path.join(data_dir, "ml_training_dataset.csv")
        train_df.to_csv(train_path, index=False)
        label_counts = train_df['risk_label'].value_counts().sort_index()
        logger.info(f"Saved {len(train_df)} rows of training data: SAFE={label_counts.get(0,0)}, WARNING={label_counts.get(1,0)}, CRITICAL={label_counts.get(2,0)}")

        # ==========================================
        # 4. Generate seed_transformers.csv (Baseline Database Snapshot)
        # ==========================================
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
