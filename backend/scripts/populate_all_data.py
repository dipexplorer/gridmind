"""
Master Data Population Script for GridMind
===========================================
This script performs three core initialization tasks:
1. Injects realistic SCADA telemetry (load_readings) for all transformers.
2. Executes the AI model (IsolationForest + SHAP) on the generated telemetry.
3. Persists TransformerScore and ShapExplanation records into the database.

Usage: Run this script when initializing a new environment or resetting demo data.
"""

import os
import sys
import uuid
import logging
import random
from typing import List, Tuple
from datetime import datetime, timezone, timedelta

# Append the parent 'backend' directory to sys.path to enable absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import SessionLocal
from models.asset import Transformer
from models.timeseries import LoadReading
from models.intelligence import TransformerScore, ShapExplanation, ScoreRunMetadata
from services.ai_service import ai_service

# Configure professional logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("DataPopulator")


def generate_scada_readings_for_transformer(transformer: Transformer, base_time: datetime) -> List[LoadReading]:
    """Generates 24 hours of synthetic SCADA readings for a single transformer."""
    readings = []
    risk = float(transformer.current_failure_risk or 0.0)
    is_anomalous = risk > 0.5 or (transformer.current_status or "").lower() in ("critical", "warning")

    # Define base sensor profiles based on asset health
    if is_anomalous:
        base_temp, base_load = random.uniform(80.0, 105.0), random.uniform(100.0, 135.0)
        base_volt, base_curr = random.uniform(350.0, 390.0), random.uniform(280.0, 380.0)
    else:
        base_temp, base_load = random.uniform(40.0, 65.0), random.uniform(30.0, 70.0)
        base_volt, base_curr = random.uniform(400.0, 420.0), random.uniform(50.0, 150.0)

    for h in range(24):
        timestamp = base_time - timedelta(hours=24 - h)
        peak_factor = 1.15 if 18 <= h <= 22 else 1.0  # Evening peak multiplier
        
        rated_kva = float(transformer.rated_kva or 315)
        load_percentage = round(base_load * peak_factor + random.uniform(-5, 5), 2)
        
        readings.append(LoadReading(
            time=timestamp,
            transformer_id=transformer.id,
            load_kw=round(rated_kva * (base_load / 100) * 0.9, 2),
            load_kvar=round(random.uniform(5.0, 20.0), 2),
            load_percentage=load_percentage,
            voltage_lv=round(base_volt + random.uniform(-5, 5), 2),
            current_a=round(base_curr * peak_factor + random.uniform(-10, 10), 2),
            temperature_c=round(base_temp + random.uniform(-3, 8) + (3.0 if 12 <= h <= 16 else 0.0), 2),
            source="SIMULATION_SCRIPT"
        ))
    return readings


def seed_scada_readings(db, transformers: List[Transformer]):
    """Generates and batch-inserts SCADA telemetry for all transformers."""
    logger.info(f"Seeding SCADA telemetry for {len(transformers)} transformers...")
    now = datetime.now(timezone.utc)
    readings_batch = []
    batch_size = 5000  # Prevent memory exhaustion during bulk inserts

    for idx, t in enumerate(transformers):
        readings_batch.extend(generate_scada_readings_for_transformer(t, now))
        
        # Execute insert in batches
        if len(readings_batch) >= batch_size or idx == len(transformers) - 1:
            db.bulk_save_objects(readings_batch)
            db.commit()
            logger.info(f"Inserted {len(readings_batch)} SCADA readings...")
            readings_batch.clear()


def run_ai_scoring(db, transformers: List[Transformer]):
    """Executes the AI scoring pipeline for all transformers."""
    logger.info(f"Running AI scoring pipeline on {len(transformers)} transformers...")
    run_id = str(uuid.uuid4())
    run_meta = ScoreRunMetadata(id=run_id, status="RUNNING")
    db.add(run_meta)
    db.commit()

    anomalies_detected = 0
    for i, t in enumerate(transformers):
        try:
            # Execute inference
            prediction = ai_service.predict_anomaly(str(t.id))
            shap_values = prediction.pop("shap_values")
            
            # Persist score
            score = TransformerScore(
                transformer_id=t.id, 
                run_id=run_id, 
                anomaly_score=prediction["anomaly_score"],
                risk_category=prediction["risk_category"], 
                expected_lifetime_days=prediction["expected_lifetime_days"],
                confidence_interval_lower=prediction["confidence_interval_lower"], 
                confidence_interval_upper=prediction["confidence_interval_upper"],
            )
            db.add(score)
            db.flush()

            # Persist SHAP explainability matrices
            for sv in shap_values:
                db.add(ShapExplanation(
                    score_id=score.id, 
                    feature_name=sv["feature_name"], 
                    feature_value=sv["feature_value"], 
                    shap_value=sv["shap_value"]
                ))

            if prediction["risk_category"] in ("HIGH", "CRITICAL"): 
                anomalies_detected += 1
                
            # Commit periodically to manage transaction size
            if (i + 1) % 100 == 0: 
                db.commit()
                logger.info(f"Scored {i+1}/{len(transformers)} transformers...")
                
        except Exception as e: 
            logger.error(f"Failed to score transformer {t.transformer_code}: {e}")
            db.rollback()

    db.commit()
    
    # Finalize run metadata
    run_meta.status = "COMPLETED"
    run_meta.completed_at = datetime.now(timezone.utc)
    run_meta.anomalies_detected = anomalies_detected
    db.commit()
    logger.info(f"AI scoring completed successfully. Detected {anomalies_detected} anomalies.")


def main():
    db = SessionLocal()
    try:
        logger.info("Initializing Master Data Population Pipeline...")
        transformers = db.query(Transformer).all()
        
        if not transformers: 
            logger.warning("No transformers found in the database. Terminating pipeline.")
            return
            
        logger.info("Purging legacy simulation data...")
        db.query(LoadReading).filter(LoadReading.source == "SIMULATION_SCRIPT").delete()
        db.commit()
        
        seed_scada_readings(db, transformers)
        run_ai_scoring(db, transformers)
        
        logger.info("Pipeline completed successfully. Dashboard is fully operational.")
    except Exception as e: 
        db.rollback()
        logger.error(f"Fatal error during pipeline execution: {e}", exc_info=True)
    finally: 
        db.close()


if __name__ == "__main__":
    main()
