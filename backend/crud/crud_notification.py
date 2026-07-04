from sqlalchemy.orm import Session
from models.notification import Notification
from schemas.notification import NotificationCreate

def create_notification(db: Session, notification: NotificationCreate):
    db_notif = Notification(**notification.model_dump())
    db.add(db_notif)
    db.commit()
    db.refresh(db_notif)
    return db_notif

def get_user_notifications(db: Session, user_id: str, limit: int = 50):
    return db.query(Notification).filter(Notification.user_id == user_id).order_by(Notification.created_at.desc()).limit(limit).all()

def mark_notification_read(db: Session, notification_id: str):
    notif = db.query(Notification).filter(Notification.id == notification_id).first()
    if notif:
        notif.is_read = True
        db.commit()
        db.refresh(notif)
    return notif
