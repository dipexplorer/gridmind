from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import date, datetime
import uuid

class LoadReadingResponse(BaseModel):
    time: datetime
    load_percentage: float
    voltage_lv: float
    current_a: float
    temperature_c: float

    model_config = ConfigDict(from_attributes=True)

class MaintenanceLogBase(BaseModel):
    maintenance_date: date
    maintenance_type: str = Field(..., max_length=32)
    components_replaced: Optional[List[str]] = None
    work_description: Optional[str] = None
    findings: Optional[str] = None
    oil_bdv_kv: Optional[float] = None
    winding_resistance: Optional[float] = None
    insulation_megohm: Optional[float] = None
    outcome: str = Field("COMPLETED", max_length=32)
    next_maintenance_due: Optional[date] = None

class MaintenanceLogCreate(MaintenanceLogBase):
    pass

class MaintenanceLogResponse(MaintenanceLogBase):
    id: uuid.UUID
    transformer_id: uuid.UUID
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
