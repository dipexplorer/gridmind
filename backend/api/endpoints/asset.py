from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from core.database import get_db
from schemas.asset import (
    SubstationCreate, SubstationResponse,
    FeederCreate, FeederResponse,
    TransformerCreate, TransformerResponse
)
from crud import crud_asset

router = APIRouter()

@router.post("/substations/", response_model=SubstationResponse)
def create_substation(substation: SubstationCreate, db: Session = Depends(get_db)):
    """
    Naya Substation (Bijli Ghar) database mein add karne ke liye API
    Frontend se jo JSON aayega, Pydantic 'substation' variable mein automatically validate karega.
    """
    return crud_asset.create_substation(db=db, substation=substation)

@router.get("/substations/", response_model=List[SubstationResponse])
def read_substations(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Database se saare Substations ki list nikalne ke liye API
    """
    return crud_asset.get_substations(db, skip=skip, limit=limit)

# --- FEEDER ENDPOINTS ---
@router.post("/feeders/", response_model=FeederResponse)
def create_feeder(feeder: FeederCreate, db: Session = Depends(get_db)):
    """
    Naya Feeder database mein add karne ke liye API
    """
    return crud_asset.create_feeder(db=db, feeder=feeder)

@router.get("/feeders/", response_model=List[FeederResponse])
def read_feeders(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Saare Feeders ki list fetch karna
    """
    return crud_asset.get_feeders(db, skip=skip, limit=limit)

# --- TRANSFORMER ENDPOINTS ---
@router.post("/transformers/", response_model=TransformerResponse)
def create_transformer(transformer: TransformerCreate, db: Session = Depends(get_db)):
    """
    Naya Transformer database mein add karne ke liye API
    """
    return crud_asset.create_transformer(db=db, transformer=transformer)

@router.get("/transformers/", response_model=List[TransformerResponse])
def read_transformers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Saare Transformers ki list fetch karna
    """
    return crud_asset.get_transformers(db, skip=skip, limit=limit)
