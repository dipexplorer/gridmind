"""
MaintenanceTicket CRUD Operations
====================================
Database operations for creating, reading, and resolving tickets.

All functions take an SQLAlchemy Session and return ORM objects.
The API layer handles serialization via Pydantic schemas.
"""

from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from models.ticket import MaintenanceTicket
from schemas.ticket import TicketCreate


def create_ticket(db: Session, ticket_in: TicketCreate) -> Optional[MaintenanceTicket]:
    """
    Create a new maintenance ticket.

    Returns the created ticket, or None if a duplicate dedup_key
    already exists (meaning an open ticket for this transformer+priority
    is already in the DB — no duplicate created).
    """
    db_ticket = MaintenanceTicket(
        transformer_id=ticket_in.transformer_id,
        priority=ticket_in.priority,
        description=ticket_in.description,
        trigger_type=ticket_in.trigger_type,
        health_score=ticket_in.health_score,
        dedup_key=ticket_in.dedup_key,
        status="OPEN",
    )
    db.add(db_ticket)
    try:
        db.commit()
        db.refresh(db_ticket)
        return db_ticket
    except IntegrityError:
        # dedup_key unique constraint violated — ticket already exists
        db.rollback()
        return None


def get_tickets(
    db: Session,
    status: Optional[str] = None,
    limit: int = 500,
) -> List[MaintenanceTicket]:
    """
    Get all tickets, optionally filtered by status.

    status: "OPEN" | "RESOLVED" | None (returns all)
    Ordered by created_at descending — newest first.
    """
    query = db.query(MaintenanceTicket)
    if status and status != "ALL":
        query = query.filter(MaintenanceTicket.status == status)
    return query.order_by(MaintenanceTicket.created_at.desc()).limit(limit).all()


def get_ticket_by_id(db: Session, ticket_id: str) -> Optional[MaintenanceTicket]:
    """Fetch a single ticket by its UUID."""
    return db.query(MaintenanceTicket).filter(
        MaintenanceTicket.id == ticket_id
    ).first()


def resolve_ticket(
    db: Session,
    ticket_id: str,
    resolution_notes: str,
    outcome: str = "COMPLETED",
) -> Optional[MaintenanceTicket]:
    """
    Mark a ticket as RESOLVED.

    Sets:
      - status → RESOLVED
      - resolved_at → current UTC time
      - resolution_notes → engineer's notes
      - outcome → what was done
      - dedup_key → None (clears it so a new ticket can be raised later
                         if the transformer degrades again)

    Returns updated ticket or None if ticket_id not found.
    """
    ticket = get_ticket_by_id(db, ticket_id)
    if not ticket:
        return None

    ticket.status = "RESOLVED"
    ticket.resolved_at = datetime.now(timezone.utc)
    ticket.resolution_notes = resolution_notes
    ticket.outcome = outcome
    # Clear dedup_key so a fresh open ticket can be created
    # for this transformer in the future if it degrades again
    ticket.dedup_key = None

    db.commit()
    db.refresh(ticket)
    return ticket


def open_ticket_exists(db: Session, dedup_key: str) -> bool:
    """
    Check whether an OPEN ticket with the given dedup_key already exists.
    Used by the batch prediction loop to avoid creating duplicates.
    """
    return db.query(MaintenanceTicket).filter(
        MaintenanceTicket.dedup_key == dedup_key,
        MaintenanceTicket.status == "OPEN",
    ).first() is not None
