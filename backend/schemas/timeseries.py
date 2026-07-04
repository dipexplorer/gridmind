from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime
import uuid

class ComplaintBase(BaseModel):
    complaint_type: str = Field(..., max_length=64)
    source: Optional[str] = Field("CALL_CENTER", max_length=32)
    severity: Optional[int] = 3
    description: Optional[str] = None
    resolved: Optional[bool] = False
    resolution_time_hrs: Optional[float] = None

class ComplaintCreate(ComplaintBase):
    transformer_id: uuid.UUID
    time: datetime

class ComplaintResponse(ComplaintBase):
    id: uuid.UUID
    transformer_id: uuid.UUID
    time: datetime
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class LoadReadingBase(BaseModel):
    load_kw: Optional[float] = None
    load_kvar: Optional[float] = None
    load_percentage: Optional[float] = None
    voltage_lv: Optional[float] = None
    current_a: Optional[float] = None
    temperature_c: Optional[float] = None
    source: Optional[str] = Field("MANUAL", max_length=32)

class LoadReadingCreate(LoadReadingBase):
    transformer_id: uuid.UUID
    time: datetime

class LoadReadingResponse(LoadReadingBase):
    transformer_id: uuid.UUID
    time: datetime
    
    model_config = ConfigDict(from_attributes=True)
