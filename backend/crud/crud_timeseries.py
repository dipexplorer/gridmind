from sqlalchemy.orm import Session
from models.timeseries import Complaint
from schemas.timeseries import ComplaintCreate

def create_complaint(db: Session, complaint: ComplaintCreate):
    db_complaint = Complaint(**complaint.model_dump())
    db.add(db_complaint)
    db.commit()
    db.refresh(db_complaint)
    return db_complaint

def get_complaints_by_transformer(db: Session, transformer_id: str, limit: int = 100):
    return db.query(Complaint).filter(Complaint.transformer_id == transformer_id).order_by(Complaint.time.desc()).limit(limit).all()
