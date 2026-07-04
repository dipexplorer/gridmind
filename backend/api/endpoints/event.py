from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
import uuid

from core.database import get_db
from schemas.event import (
    MaintenanceLogCreate, MaintenanceLogResponse,
    FailureEventCreate, FailureEventResponse
)
from crud import crud_event

router = APIRouter()

@router.post("/maintenance-logs/", response_model=MaintenanceLogResponse)
def add_maintenance_log(log: MaintenanceLogCreate, db: Session = Depends(get_db)):
    """
    Jab field engineer transformer repair karke wapas aayega, toh wo yahan se log enter karega.
    """
    return crud_event.create_maintenance_log(db=db, log=log)

@router.get("/transformers/{transformer_id}/maintenance-logs/", response_model=List[MaintenanceLogResponse])
def get_transformer_maintenance(transformer_id: uuid.UUID, limit: int = 100, db: Session = Depends(get_db)):
    """
    Ek transformer ki poori repair/maintenance history dekhne ke liye API.
    """
    return crud_event.get_maintenance_logs_by_transformer(db, transformer_id=str(transformer_id), limit=limit)

@router.post("/failure-events/", response_model=FailureEventResponse)
def add_failure_event(event: FailureEventCreate, db: Session = Depends(get_db)):
    """
    Jab transformer fail ya blast ho jaye, toh event yahan record hoga.
    Ye data AI model ko sikhane ke liye sabse zaroori hai ki transformers fail kyun hote hain.
    """
    return crud_event.create_failure_event(db=db, event=event)

@router.get("/transformers/{transformer_id}/failure-events/", response_model=List[FailureEventResponse])
def get_transformer_failures(transformer_id: uuid.UUID, limit: int = 100, db: Session = Depends(get_db)):
    """
    Transformer past mein kab-kab fail hua hai, uski list nikalne ke liye.
    """
    return crud_event.get_failure_events_by_transformer(db, transformer_id=str(transformer_id), limit=limit)
