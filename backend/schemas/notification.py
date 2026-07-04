from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime
import uuid

class NotificationBase(BaseModel):
    title: str = Field(..., max_length=128)
    message: str
    notification_type: str = Field(..., max_length=32)
    priority: str = Field("LOW", max_length=16)
    is_read: bool = False

class NotificationCreate(NotificationBase):
    user_id: uuid.UUID
    transformer_id: Optional[uuid.UUID] = None

class NotificationResponse(NotificationBase):
    id: uuid.UUID
    user_id: uuid.UUID
    transformer_id: Optional[uuid.UUID]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
