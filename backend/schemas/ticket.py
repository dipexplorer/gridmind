"""
MaintenanceTicket Pydantic Schemas
====================================
Used by FastAPI for request validation and response serialization.

TicketCreate  → what fields are needed to create a ticket
TicketResolve → what engineer submits when resolving
TicketResponse → what the API returns to the frontend
"""

from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
import uuid


class TicketCreate(BaseModel):
    """Fields required to create a new maintenance ticket."""
    transformer_id: str
    priority: str              # "CRITICAL" | "HIGH"
    description: str
    trigger_type: str = "AUTO" # "AUTO" | "MANUAL"
    health_score: Optional[float] = None
    dedup_key: Optional[str] = None


class TicketResolve(BaseModel):
    """Payload submitted by an engineer when closing a ticket."""
    resolution_notes: str
    outcome: str = "COMPLETED"  # COMPLETED | REPAIRED | REPLACED | MONITORED


class TicketResponse(BaseModel):
    """Full ticket object returned to the frontend."""
    id: uuid.UUID
    transformer_id: str
    status: str
    priority: str
    description: str
    trigger_type: str
    health_score: Optional[float] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    outcome: Optional[str] = None
    dedup_key: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
