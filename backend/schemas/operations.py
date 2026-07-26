from pydantic import BaseModel, UUID4
from typing import Optional, List
from datetime import datetime, date

class AlertResponse(BaseModel):
    id: UUID4
    transformer_id: UUID4
    severity: str
    message: str
    is_acknowledged: bool
    acknowledged_by: Optional[UUID4]
    acknowledged_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        orm_mode = True

class TicketResponse(BaseModel):
    id: UUID4
    transformer_id: UUID4
    alert_id: Optional[UUID4]
    status: str
    priority: str
    assigned_to: Optional[UUID4]
    due_date: Optional[date]
    description: Optional[str]
    resolution_notes: Optional[str]
    resolved_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        orm_mode = True

class TicketResolveRequest(BaseModel):
    resolution_notes: str
    outcome: str = "COMPLETED"
