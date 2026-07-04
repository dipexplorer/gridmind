from sqlalchemy.orm import Session
from models.event import MaintenanceLog, FailureEvent
from schemas.event import MaintenanceLogCreate, FailureEventCreate

def create_maintenance_log(db: Session, log: MaintenanceLogCreate):
    db_log = MaintenanceLog(**log.model_dump())
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log

def get_maintenance_logs_by_transformer(db: Session, transformer_id: str, limit: int = 100):
    return db.query(MaintenanceLog).filter(MaintenanceLog.transformer_id == transformer_id).order_by(MaintenanceLog.performed_at.desc()).limit(limit).all()

def create_failure_event(db: Session, event: FailureEventCreate):
    db_event = FailureEvent(**event.model_dump())
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event

def get_failure_events_by_transformer(db: Session, transformer_id: str, limit: int = 100):
    return db.query(FailureEvent).filter(FailureEvent.transformer_id == transformer_id).order_by(FailureEvent.failed_at.desc()).limit(limit).all()
