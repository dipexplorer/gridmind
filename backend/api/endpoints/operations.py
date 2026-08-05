"""
Operations API — Maintenance Tickets
======================================
REST endpoints for the Tickets page (/dashboard/tickets).

GET  /operations/tickets         → List all tickets (filter by status)
POST /operations/tickets/{id}/resolve → Engineer resolves a ticket
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from core.database import get_db
from crud.crud_ticket import get_tickets, resolve_ticket, get_ticket_by_id
from schemas.ticket import TicketResponse, TicketResolve

router = APIRouter()


@router.get("/tickets", response_model=List[TicketResponse])
def get_all_tickets(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Return maintenance tickets, optionally filtered by status.

    Query params:
      ?status=OPEN       → only open tickets
      ?status=RESOLVED   → only resolved tickets
      (none)             → all tickets, newest first
    """
    return get_tickets(db, status=status)


@router.post("/tickets/{ticket_id}/resolve", response_model=TicketResponse)
def resolve_ticket_endpoint(
    ticket_id: str,
    payload: TicketResolve,
    db: Session = Depends(get_db),
):
    """
    Mark a ticket as RESOLVED.

    Requires:
      - resolution_notes: what the engineer did
      - outcome: COMPLETED | REPAIRED | REPLACED | MONITORED
    """
    # Check ticket exists first
    existing = get_ticket_by_id(db, ticket_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")

    if existing.status == "RESOLVED":
        raise HTTPException(status_code=400, detail="Ticket is already resolved")

    updated = resolve_ticket(
        db,
        ticket_id=ticket_id,
        resolution_notes=payload.resolution_notes,
        outcome=payload.outcome,
    )
    return updated
