from sqlalchemy.orm import Session
from models.intelligence import ScoreRunMetadata, TransformerScore, ShapExplanation
from datetime import datetime, timezone

def get_latest_score_run(db: Session):
    return db.query(ScoreRunMetadata).order_by(ScoreRunMetadata.started_at.desc()).first()

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
            cat = "HIGH"
            lifetime_days = 30
        elif status == "normal":
            # Further refine based on actual score
            if anomaly_score_pct >= 70:
                cat = "CRITICAL"
                lifetime_days = 7
            elif anomaly_score_pct >= 40:
                cat = "HIGH"
                lifetime_days = 30
            elif anomaly_score_pct >= 20:
                cat = "MEDIUM"
                lifetime_days = 90
            else:
                cat = "LOW"
                lifetime_days = 365
        else:
            cat = "LOW"
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
    return db.query(ShapExplanation).filter(ShapExplanation.score_id == score_id).all()

# --- Write Operations for Celery Background Worker ---

def create_score_run(db: Session, run_id: str):
    run = ScoreRunMetadata(
        id=run_id,
        status="RUNNING"
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run

def update_score_run(db: Session, run_id: str, status: str, anomalies_detected: int = 0):
    run = db.query(ScoreRunMetadata).filter(ScoreRunMetadata.id == run_id).first()
    if run:
        run.status = status
        run.completed_at = datetime.now(timezone.utc)
        run.anomalies_detected = anomalies_detected
        db.commit()
        db.refresh(run)
    return run

def create_transformer_score(db: Session, run_id: str, data: dict, shap_values: list):
    score = TransformerScore(
        transformer_id=data["transformer_id"],
        run_id=run_id,
        anomaly_score=data["anomaly_score"],
        risk_category=data["risk_category"],
        expected_lifetime_days=data["expected_lifetime_days"],
        confidence_interval_lower=data["confidence_interval_lower"],
        confidence_interval_upper=data["confidence_interval_upper"]
    )
    db.add(score)
    db.flush() # flush to get score.id
    
    # Insert SHAP explanations
    for shap in shap_values:
        explanation = ShapExplanation(
            score_id=score.id,
            feature_name=shap["feature_name"],
            feature_value=shap["feature_value"],
            shap_value=shap["shap_value"]
        )
        db.add(explanation)
        
    db.commit()
    return score
