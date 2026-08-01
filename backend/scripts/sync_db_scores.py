import sys
import os
import uuid
import logging

# Add backend directory to PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import SessionLocal
from crud import crud_asset
from services.ai_service import ai_service
from models.asset import Transformer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def sync_all():
    db = SessionLocal()
    try:
        transformers = db.query(Transformer).all()
        logger.info(f"Syncing ML scores for {len(transformers)} transformers...")
        for i, t in enumerate(transformers):
            # Run inference
            pred = ai_service.predict_anomaly(str(t.id))
            
            # Update the DB record directly
            t.current_health_score = pred.get("health_score")
            t.current_failure_risk = pred.get("failure_probability", 0) / 100.0  # Normalize to 0-1 range for the DB
            t.expected_lifetime_days = pred.get("expected_lifetime_days")
            t.current_status = pred.get("risk_category")
            
            if i % 100 == 0:
                logger.info(f"Synced {i}/{len(transformers)}...")
                db.commit()
                
        db.commit()
        logger.info("Done syncing all transformers!")
    finally:
        db.close()

if __name__ == "__main__":
    sync_all()
