"""
GridMind 24-Hour Batch Prediction Script
=======================================
This script runs a complete 24-hour evaluation cycle for all transformers:
1. Queries the latest 24 SCADA telemetry entries (load_readings) for each transformer.
2. Runs batch Isolation Forest and Cox survival analysis over the 24-hour window.
3. Updates the `transformers` table with daily aggregated health, status, and failure risks.
4. Persists the historical `TransformerScore` and SHAP explanations for detailed pages.

Run manually or via scheduler to update dashboard status.
"""

import os
import sys
import uuid
import logging
from datetime import datetime, timezone

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import SessionLocal
from models.asset import Transformer
from models.timeseries import LoadReading
from models.intelligence import TransformerScore, ShapExplanation, ScoreRunMetadata
from services.ai_service import ai_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("DailyBatchPredictor")


def run_batch_prediction():
    db = SessionLocal()
    try:
        logger.info("Initializing Daily Batch ML Prediction Run...")
        transformers = db.query(Transformer).all()
        if not transformers:
            logger.warning("No transformers found in database. Terminating.")
            return

        run_id = str(uuid.uuid4())
        run_meta = ScoreRunMetadata(id=run_id, status="RUNNING")
        db.add(run_meta)
        db.commit()

        anomalies_detected = 0
        updated_count = 0

        for idx, t in enumerate(transformers):
            try:
                # Fetch latest 24 readings to represent the last 24 hours
                readings = db.query(LoadReading)\
                    .filter(LoadReading.transformer_id == t.id)\
                    .order_by(LoadReading.time.desc())\
                    .limit(24)\
                    .all()

                if not readings:
                    logger.warning(f"No telemetry found for transformer {t.transformer_code}. Skipping.")
                    continue

                # Run Batch ML Predictor
                pred = ai_service.predict_daily_health(str(t.id), readings)
                shap_values = pred.pop("shap_values", [])

                # Translate predictions to database properties
                anomaly_score = pred["anomaly_score"]
                risk_category = pred["risk_category"]
                failure_risk = anomaly_score / 100.0
                health_score = int(100 - anomaly_score)

                # Update main transformer entry
                t.current_failure_risk = failure_risk
                t.current_health_score = health_score
                t.current_status = risk_category.lower()
                t.current_load_pct = pred.get("avg_load_pct", t.current_load_pct)
                t.current_oil_temp_c = pred.get("avg_temp_c", t.current_oil_temp_c)
                t.last_updated = datetime.now(timezone.utc)

                # Log score history for analytics/detail screens
                score = TransformerScore(
                    transformer_id=t.id,
                    run_id=run_id,
                    anomaly_score=anomaly_score,
                    risk_category=risk_category,
                    expected_lifetime_days=pred["expected_lifetime_days"],
                    confidence_interval_lower=pred["confidence_interval_lower"],
                    confidence_interval_upper=pred["confidence_interval_upper"]
                )
                db.add(score)
                db.flush()

                # Save SHAP feature explainability lists
                for sv in shap_values:
                    db.add(ShapExplanation(
                        score_id=score.id,
                        feature_name=sv["feature_name"],
                        feature_value=sv["feature_value"],
                        shap_value=sv["shap_value"]
                    ))

                if risk_category in ("HIGH", "CRITICAL"):
                    anomalies_detected += 1
                updated_count += 1

                # Periodic commits
                if (idx + 1) % 100 == 0:
                    db.commit()
                    logger.info(f"Processed {idx + 1}/{len(transformers)} transformers...")

            except Exception as tr_err:
                logger.error(f"Failed to process transformer {t.transformer_code}: {tr_err}")
                db.rollback()

        db.commit()

        # Update run metadata
        run_meta.status = "COMPLETED"
        run_meta.completed_at = datetime.now(timezone.utc)
        run_meta.anomalies_detected = anomalies_detected
        db.commit()

        logger.info(f"Daily batch run completed successfully. Updated {updated_count} transformers. Detected {anomalies_detected} anomalies.")

    except Exception as e:
        db.rollback()
        logger.error(f"Fatal error during batch prediction execution: {e}", exc_info=True)
    finally:
        db.close()


if __name__ == "__main__":
    run_batch_prediction()
