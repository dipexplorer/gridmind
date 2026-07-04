from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime
import uuid

class MaintenanceLogBase(BaseModel):
    activity_type: str = Field(..., max_length=64)
    description: Optional[str] = None
    cost: Optional[float] = None
    performed_at: datetime
    performed_by: Optional[str] = Field(None, max_length=128)
    parts_replaced: Optional[str] = None
    next_maintenance_due: Optional[datetime] = None

class MaintenanceLogCreate(MaintenanceLogBase):
    transformer_id: uuid.UUID

class MaintenanceLogResponse(MaintenanceLogBase):
    id: uuid.UUID
    transformer_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class FailureEventBase(BaseModel):
    failure_mode: str = Field(..., max_length=64)
    failure_cause: Optional[str] = Field(None, max_length=128)
    failed_at: datetime
    description: Optional[str] = None
    downtime_hrs: Optional[float] = None
    repair_cost: Optional[float] = None

class FailureEventCreate(FailureEventBase):
    transformer_id: uuid.UUID

class FailureEventResponse(FailureEventBase):
    id: uuid.UUID
    transformer_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
