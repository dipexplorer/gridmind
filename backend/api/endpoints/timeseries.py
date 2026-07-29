from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
import uuid

from core.database import get_db
from schemas.timeseries import (
    ComplaintCreate, ComplaintResponse
)
from crud import crud_timeseries

router = APIRouter()

@router.post("/complaints/", response_model=ComplaintResponse)
def add_complaint(complaint: ComplaintCreate, db: Session = Depends(get_db)):
    """
    Agar public complaint karti hai, toh wo system mein yahan se add hogi.
    """
    return crud_timeseries.create_complaint(db=db, complaint=complaint)

@router.get("/transformers/{transformer_id}/complaints/", response_model=List[ComplaintResponse])
def get_transformer_complaints(transformer_id: uuid.UUID, limit: int = 100, db: Session = Depends(get_db)):
    """
    Kisi transformer par kitni complaints aayi hain, ye dekhne ke liye API.
    """
    return crud_timeseries.get_complaints_by_transformer(db, transformer_id=str(transformer_id), limit=limit)
