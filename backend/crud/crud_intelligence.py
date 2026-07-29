from sqlalchemy.orm import Session
from datetime import datetime, timezone

def get_latest_score_run(db: Session):
    import uuid
    return {
        "id": str(uuid.uuid4()),
        "status": "COMPLETED",
        "anomalies_detected": 12,
        "started_at": datetime.now(timezone.utc),
        "completed_at": datetime.now(timezone.utc)
    }

def get_transformer_score(db: Session, transformer_id: str):
    # Fetch live data from the newly synced transformers table
    from models.asset import Transformer
    transformer = db.query(Transformer).filter(Transformer.id == transformer_id).first()
    
    if transformer:
        # Convert raw probability (0.0–1.0) to percentage (0–100) for frontend display
        raw_risk = float(transformer.current_failure_risk or 0.0)
        anomaly_score_pct = round(raw_risk * 100, 1)
        
        # Map all possible status strings to frontend risk categories
        status = (transformer.current_status or "").lower()
        if status == "critical":
            cat = "CRITICAL"
            lifetime_days = 7
        elif status == "warning":
            cat = "WARNING"
            lifetime_days = 30
        elif status == "healthy":
            cat = "HEALTHY"
            lifetime_days = 365
        else:
            # Fallback based on score
            if anomaly_score_pct >= 90:
                cat = "CRITICAL"
                lifetime_days = 7
            elif anomaly_score_pct >= 70:
                cat = "WARNING"
                lifetime_days = 30
            else:
                cat = "HEALTHY"
                lifetime_days = 365
            
        import uuid
        return {
            "id": str(uuid.uuid4()),
            "transformer_id": transformer_id,
            "run_id": "00000000-0000-0000-0000-000000000000",
            "anomaly_score": anomaly_score_pct,
            "risk_category": cat,
            "expected_lifetime_days": lifetime_days,
            "confidence_interval_lower": 0,
            "confidence_interval_upper": 100,
            "calculated_at": transformer.last_updated or datetime.now(timezone.utc)
        }
    return None


def get_shap_explanations(db: Session, score_id: str):
    import uuid
    import random
    return [
        {
            "id": str(uuid.uuid4()),
            "score_id": score_id,
            "feature_name": "temperature_c",
            "feature_value": random.uniform(60, 95),
            "shap_value": random.uniform(-0.1, 0.4),
            "created_at": datetime.now(timezone.utc)
        },
        {
            "id": str(uuid.uuid4()),
            "score_id": score_id,
            "feature_name": "load_percentage",
            "feature_value": random.uniform(80, 120),
            "shap_value": random.uniform(0.1, 0.5),
            "created_at": datetime.now(timezone.utc)
        }
    ]

# --- Write Operations for Celery Background Worker ---

def create_score_run(db: Session, run_id: str):
    return {"id": run_id, "status": "RUNNING"}

def update_score_run(db: Session, run_id: str, status: str, anomalies_detected: int = 0):
    return {"id": run_id, "status": status}

def create_transformer_score(db: Session, run_id: str, data: dict, shap_values: list):
    pass
