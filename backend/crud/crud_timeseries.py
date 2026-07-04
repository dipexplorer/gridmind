from sqlalchemy.orm import Session
from models.timeseries import LoadReading, Complaint
from schemas.timeseries import LoadReadingCreate, ComplaintCreate

def create_load_reading(db: Session, load_reading: LoadReadingCreate):
    db_load = LoadReading(**load_reading.model_dump())
    db.add(db_load)
    db.commit()
    db.refresh(db_load)
    return db_load

def get_load_readings_by_transformer(db: Session, transformer_id: str, limit: int = 100):
    return db.query(LoadReading).filter(LoadReading.transformer_id == transformer_id).order_by(LoadReading.time.desc()).limit(limit).all()

def create_complaint(db: Session, complaint: ComplaintCreate):
    db_complaint = Complaint(**complaint.model_dump())
    db.add(db_complaint)
    db.commit()
    db.refresh(db_complaint)
    return db_complaint

def get_complaints_by_transformer(db: Session, transformer_id: str, limit: int = 100):
    return db.query(Complaint).filter(Complaint.transformer_id == transformer_id).order_by(Complaint.time.desc()).limit(limit).all()
