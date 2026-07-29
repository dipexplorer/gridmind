from fastapi import APIRouter
from typing import List
import uuid

router = APIRouter()

@router.get("/tickets", response_model=List[dict])
def get_all_tickets(status: str = None):
    """
    Get all maintenance tickets (Deprecated, returns empty list).
    """
    return []

@router.post("/tickets/{ticket_id}/resolve", response_model=dict)
def resolve_ticket(ticket_id: uuid.UUID):
    """
    Resolve a ticket (Deprecated).
    """
    return {}

@router.get("/alerts", response_model=List[dict])
def get_alerts(unacknowledged_only: bool = True):
    """
    Get high-priority alerts (Deprecated, returns empty list).
    """
    return []
