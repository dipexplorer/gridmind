from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import uuid

from core.database import get_db
from schemas.intelligence import (
    ScoreRunMetadataResponse, 
    TransformerScoreResponse, 
    ShapExplanationResponse
)
from crud import crud_intelligence
from tasks.scoring import score_all_transformers

router = APIRouter()

@router.post("/ai-runs/trigger")
def trigger_ai_run():
    """
    Trigger a new AI background run via Celery.
    Returns the task_id immediately.
    """
    task_id = str(uuid.uuid4())
    # Send task to Celery Queue
    score_all_transformers.apply_async(kwargs={"task_id": task_id}, task_id=task_id)
    
    return {"message": "AI analysis started in background", "task_id": task_id}

@router.get("/ai-runs/latest", response_model=ScoreRunMetadataResponse)
def get_latest_ai_run(db: Session = Depends(get_db)):
    """
    Check karna ki AI ne aakhiri baar predictions kab run kiye the.
    """
    run = crud_intelligence.get_latest_score_run(db)
    if not run:
        raise HTTPException(status_code=404, detail="No AI runs found yet")
    return run

@router.get("/transformers/{transformer_id}/risk-score", response_model=TransformerScoreResponse)
def get_transformer_risk_score(transformer_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Ek specific transformer ka sabse latest Risk Score aur category nikalna.
    """
    score = crud_intelligence.get_transformer_score(db, str(transformer_id))
    if not score:
        raise HTTPException(status_code=404, detail="Risk score not available for this transformer")
    return score

@router.get("/scores/{score_id}/shap-explanations", response_model=List[ShapExplanationResponse])
def get_score_explanations(score_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    SHAP values fetch karna. Ye batata hai ki AI ne particular transformer ko High Risk kyu bola.
    (For example: Temperature high hone ka kitna asar tha)
    """
    return crud_intelligence.get_shap_explanations(db, str(score_id))
