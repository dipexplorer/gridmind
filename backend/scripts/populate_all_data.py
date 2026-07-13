"""
Master Data Population Script for GridMind
===========================================
Yeh script in 3 kaam karta hai:
1. Saare transformers ke liye realistic SCADA telemetry inject karta hai (load_readings table)
2. AI model (IsolationForest + SHAP) directly run karta hai
3. TransformerScore + ShapExplanation database mein save karta hai

Result: Dashboard par SCADA chart, SHAP bars, aur Risk Score sab LIVE data se chalenge.
"""

import os, sys, uuid, logging
from datetime import datetime, timezone, timedelta
import random

# Add parent 'backend' directory to sys.path so we can import models/services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logging.basicConfig(level=logging.ERROR)

from core.config import settings
from core.database import SessionLocal
from models.asset import Transformer
from models.timeseries import LoadReading
from models.intelligence import TransformerScore, ShapExplanation, ScoreRunMetadata
from services.ai_service import ai_service

def seed_scada_readings(db, transformers):
    print(f"📡 Seeding SCADA telemetry for {len(transformers)} transformers...")
    now = datetime.now(timezone.utc)
    readings = []

    for t in transformers:
        risk = float(t.current_failure_risk or 0.0)
        is_anomalous = risk > 0.5 or (t.current_status or "").lower() in ("critical", "warning")

        if is_anomalous:
            base_temp, base_load, base_volt, base_curr = random.uniform(80.0, 105.0), random.uniform(100.0, 135.0), random.uniform(350.0, 390.0), random.uniform(280.0, 380.0)
        else:
            base_temp, base_load, base_volt, base_curr = random.uniform(40.0, 65.0), random.uniform(30.0, 70.0), random.uniform(400.0, 420.0), random.uniform(50.0, 150.0)

        for h in range(24):
            ts = now - timedelta(hours=24-h)
            peak_factor = 1.15 if 18 <= h <= 22 else 1.0
            readings.append(LoadReading(
                time=ts,
                transformer_id=t.id,
                load_kw=round(float(t.rated_kva or 315) * (base_load / 100) * 0.9, 2),
                load_kvar=round(random.uniform(5.0, 20.0), 2),
                load_percentage=round(base_load * peak_factor + random.uniform(-5, 5), 2),
                voltage_lv=round(base_volt + random.uniform(-5, 5), 2),
                current_a=round(base_curr * peak_factor + random.uniform(-10, 10), 2),
                temperature_c=round(base_temp + random.uniform(-3, 8) + (3.0 if 12 <= h <= 16 else 0.0), 2),
                source="SIMULATION_SCRIPT"
            ))
    db.bulk_save_objects(readings)
    db.commit()

def run_ai_scoring(db, transformers):
    print(f"\n🤖 Running AI scoring pipeline on {len(transformers)} transformers...")
    run_id = str(uuid.uuid4())
    run_meta = ScoreRunMetadata(id=run_id, status="RUNNING")
    db.add(run_meta)
    db.commit()

    anomalies = 0
    for i, t in enumerate(transformers):
        try:
            prediction = ai_service.predict_anomaly(str(t.id))
            shap_values = prediction.pop("shap_values")
            score = TransformerScore(
                transformer_id=t.id, run_id=run_id, anomaly_score=prediction["anomaly_score"],
                risk_category=prediction["risk_category"], expected_lifetime_days=prediction["expected_lifetime_days"],
                confidence_interval_lower=prediction["confidence_interval_lower"], confidence_interval_upper=prediction["confidence_interval_upper"],
            )
            db.add(score)
            db.flush()

            for sv in shap_values:
                db.add(ShapExplanation(score_id=score.id, feature_name=sv["feature_name"], feature_value=sv["feature_value"], shap_value=sv["shap_value"]))

            if prediction["risk_category"] in ("HIGH", "CRITICAL"): anomalies += 1
            if (i + 1) % 50 == 0: db.commit()
        except Exception: db.rollback()

    db.commit()
    run_meta.status = "COMPLETED"
    run_meta.completed_at = datetime.now(timezone.utc)
    run_meta.anomalies_detected = anomalies
    db.commit()

def main():
    db = SessionLocal()
    try:
        transformers = db.query(Transformer).all()
        if not transformers: return
        db.query(LoadReading).filter(LoadReading.source == "SIMULATION_SCRIPT").delete()
        db.commit()
        seed_scada_readings(db, transformers)
        run_ai_scoring(db, transformers)
    except Exception as e: db.rollback()
    finally: db.close()

if __name__ == "__main__":
    main()
