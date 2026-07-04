from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uuid

from core.database import get_db
from schemas.notification import NotificationCreate, NotificationResponse
from crud import crud_notification

router = APIRouter()

@router.post("/notifications/", response_model=NotificationResponse)
def create_notification(notification: NotificationCreate, db: Session = Depends(get_db)):
    """
    System (ya AI) ke dwara engineer ko alert (notification) bhejne ke liye.
    """
    return crud_notification.create_notification(db=db, notification=notification)

@router.get("/users/{user_id}/notifications/", response_model=List[NotificationResponse])
def read_user_notifications(user_id: uuid.UUID, limit: int = 50, db: Session = Depends(get_db)):
    """
    Kisi specific engineer ke saare alerts aur messages dekhne ke liye.
    """
    return crud_notification.get_user_notifications(db, user_id=str(user_id), limit=limit)

@router.patch("/notifications/{notification_id}/read", response_model=NotificationResponse)
def mark_as_read(notification_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Jab engineer alert dekh lega, toh ye api us notification ko 'Read' mark kar degi (taaki baar baar popup na aaye).
    """
    notif = crud_notification.mark_notification_read(db, notification_id=str(notification_id))
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notif
