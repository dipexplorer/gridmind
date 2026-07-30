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

            status = (t.current_status or "").lower()
            is_critical = status == "critical"
            is_warning = status == "warning"

            for h in range(24):
                time_pt = now - timedelta(hours=(23 - h))
                hour = time_pt.hour

                # Deterministic seed using transformer ID and hour to make it reproducible
                seed_str = f"{t.id}_{time_pt.strftime('%Y%m%d%H')}"
                local_random = random.Random(seed_str)

                if is_critical:
                    temp = ambient_temp + local_random.uniform(55, 75)
                    load = local_random.uniform(105, 135)
                    voltage = local_random.uniform(350, 375)
                elif is_warning:
                    temp = ambient_temp + local_random.uniform(35, 55)
                    load = local_random.uniform(85, 110)
                    voltage = local_random.uniform(370, 395)
                else:
                    temp_offset = local_random.uniform(5, 12) if 11 <= hour <= 16 else local_random.uniform(0, 4)
                    temp = ambient_temp + temp_offset + local_random.uniform(-1, 1)
                    load = local_random.uniform(40, 80)
                    voltage = local_random.uniform(405, 420)

                base_current = (float(t.rated_kva) * 1000.0) / (415.0 * 1.732) if t.rated_kva else 139.0
                current = base_current * (load / 100.0) + local_random.uniform(-5, 5)

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
        # 3. Generate ml_training_dataset.csv
        # ==========================================
        logger.info("Generating ml_training_dataset.csv (10,000 samples)...")
        n_samples = 10000
        np.random.seed(42)

        temp_c = np.random.uniform(30.0, 110.0, n_samples)
        load_pct = np.random.uniform(15.0, 140.0, n_samples)
        voltage_lv = np.random.uniform(350.0, 430.0, n_samples)
        current_a = np.random.uniform(20.0, 400.0, n_samples)

        labels = np.zeros(n_samples, dtype=int)  # Default: SAFE (0)

        warning_mask = (
            (temp_c > 70) & (temp_c <= 85) |
            (load_pct > 80) & (load_pct <= 95) |
            (voltage_lv < 385)
        )
        critical_mask = (
            ((temp_c > 85) & (load_pct > 90)) |
            ((temp_c > 90) & (voltage_lv < 380)) |
            (load_pct > 110)
        )

        labels[warning_mask] = 1   # WARNING
        labels[critical_mask] = 2  # CRITICAL

        # Add 3% noise to class labels to reflect real-world overlapping
        noise_idx = np.random.choice(n_samples, size=int(n_samples * 0.03), replace=False)
        labels[noise_idx] = np.random.randint(0, 3, size=len(noise_idx))

        train_df = pd.DataFrame({
            "temperature_c": np.round(temp_c, 2),
            "load_percentage": np.round(load_pct, 2),
            "voltage_lv": np.round(voltage_lv, 1),
            "current_a": np.round(current_a, 1),
            "risk_label": labels
        })

        train_path = os.path.join(data_dir, "ml_training_dataset.csv")
        train_df.to_csv(train_path, index=False)
        logger.info(f"Saved {len(train_df)} rows of training data to {train_path}")

        # ==========================================
        # 4. Generate seed_transformers.csv (Baseline Database Snapshot)
        # ==========================================
        logger.info("Generating seed_transformers.csv...")
        seed_rows = []

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

            sub = db.query(Substation).filter(Substation.id == t.substation_id).first()
            fd = db.query(Feeder).filter(Feeder.id == t.feeder_id).first()

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
