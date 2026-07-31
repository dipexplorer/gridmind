"""
GridMind Intelligence CRUD
===========================
Thin delegation layer. All business logic lives in InferenceService.

This file exists only to maintain the existing import contract:
    from crud import crud_intelligence
"""
from sqlalchemy.orm import Session
from datetime import datetime, timezone


def get_latest_score_run(db: Session):
    """Return a lightweight run metadata stub."""
    import uuid
    return {
        "id": str(uuid.uuid4()),
        "status": "COMPLETED",
        "anomalies_detected": 0,
        "started_at": datetime.now(timezone.utc),
        "completed_at": datetime.now(timezone.utc),
    }


def get_transformer_score(db: Session, transformer_id: str):
    """
    Delegate to InferenceService for full 4-model fusion scoring.
    Returns None if transformer not found or no telemetry available.
    """
    from services.inference_service import inference_service
    return inference_service.score_transformer(transformer_id, db)


def get_shap_explanations(db: Session, score_id: str):
    """
    SHAP values are now embedded in the /risk-score response itself.
    This endpoint is kept for backward API compatibility but returns [].
    Clients should read shap_values from the TransformerScoreResponse.
    """
    return []


# --- Write Operations for Celery Background Worker ---

def create_score_run(db: Session, run_id: str):
    return {"id": run_id, "status": "RUNNING"}


def update_score_run(db: Session, run_id: str, status: str, anomalies_detected: int = 0):
    return {"id": run_id, "status": status}


# Removed: create_transformer_score() — was dead `pass` code.
# If score persistence is needed later, implement here with SQLAlchemy ORM writes.
