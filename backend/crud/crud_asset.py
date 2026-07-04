from sqlalchemy.orm import Session
from models.asset import Substation, Feeder, Transformer
from schemas.asset import (
    SubstationCreate, 
    FeederCreate, 
    TransformerCreate
)

def create_substation(db: Session, substation: SubstationCreate):
    # Pydantic schema (data guard) se data nikalkar SQLAlchemy model (database table) mein bhejna
    db_substation = Substation(**substation.model_dump())
    db.add(db_substation)
    db.commit()
    db.refresh(db_substation) # Nayi ID (UUID) aur created_at fetch karne ke liye
    return db_substation

def get_substations(db: Session, skip: int = 0, limit: int = 100):
    # Database se saare substations fetch karna (pagination ke saath)
    return db.query(Substation).offset(skip).limit(limit).all()

# --- FEEDER CRUD ---
def create_feeder(db: Session, feeder: FeederCreate):
    db_feeder = Feeder(**feeder.model_dump())
    db.add(db_feeder)
    db.commit()
    db.refresh(db_feeder)
    return db_feeder

def get_feeders(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Feeder).offset(skip).limit(limit).all()

# --- TRANSFORMER CRUD ---
def create_transformer(db: Session, transformer: TransformerCreate):
    db_transformer = Transformer(**transformer.model_dump())
    db.add(db_transformer)
    db.commit()
    db.refresh(db_transformer)
    return db_transformer

def get_transformers(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Transformer).offset(skip).limit(limit).all()
