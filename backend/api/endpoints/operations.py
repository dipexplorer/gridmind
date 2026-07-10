from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uuid
from datetime import datetime

from core.database import get_db
from models.event import MaintenanceTicket, Alert, MaintenanceLog
from schemas.operations import TicketResponse, AlertResponse, TicketResolveRequest

router = APIRouter()

@router.get("/tickets", response_model=List[TicketResponse])
def get_all_tickets(status: str = None, db: Session = Depends(get_db)):
    """
    Get all maintenance tickets.
    """
    query = db.query(MaintenanceTicket)
    if status:
        query = query.filter(MaintenanceTicket.status == status)
    return query.order_by(MaintenanceTicket.created_at.desc()).all()

@router.post("/tickets/{ticket_id}/resolve", response_model=TicketResponse)
def resolve_ticket(ticket_id: uuid.UUID, req: TicketResolveRequest, db: Session = Depends(get_db)):
    """
    Resolve a ticket and automatically create a maintenance log.
    """
    ticket = db.query(MaintenanceTicket).filter(MaintenanceTicket.id == str(ticket_id)).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
        
    if ticket.status == "RESOLVED":
        raise HTTPException(status_code=400, detail="Ticket is already resolved")

    ticket.status = "RESOLVED"
    ticket.resolution_notes = req.resolution_notes
    ticket.resolved_at = datetime.utcnow()
    
    # Generate Maintenance Log
    log = MaintenanceLog(
        transformer_id=ticket.transformer_id,
        maintenance_date=datetime.utcnow().date(),
        maintenance_type="AI_PREDICTIVE_FIX",
        work_description=req.resolution_notes,
        outcome=req.outcome
    )
    db.add(log)
    
    # Acknowledge the associated alert if exists
    if ticket.alert_id:
        alert = db.query(Alert).filter(Alert.id == ticket.alert_id).first()
        if alert:
            alert.is_acknowledged = True
            alert.acknowledged_at = datetime.utcnow()
            
    db.commit()
    db.refresh(ticket)
    return ticket

@router.get("/alerts", response_model=List[AlertResponse])
def get_alerts(unacknowledged_only: bool = True, db: Session = Depends(get_db)):
    """
    Get high-priority alerts.
    """
    query = db.query(Alert)
    if unacknowledged_only:
        query = query.filter(Alert.is_acknowledged == False)
    return query.order_by(Alert.created_at.desc()).all()
