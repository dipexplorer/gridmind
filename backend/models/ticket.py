"""
MaintenanceTicket — SQLAlchemy ORM Model
==========================================
Represents a maintenance work order raised for a transformer.

Tickets are created in two ways:
  1. AUTOMATICALLY — by predict_daily_batch.py when a transformer
     reaches CRITICAL or WARNING status. One open ticket per transformer
     per status type is allowed (dedup_key enforces this).
  2. MANUALLY — reserved for future implementation via the detail page.

Columns:
  transformer_id  → which transformer needs work
  status          → OPEN (pending) | RESOLVED (done)
  priority        → CRITICAL | HIGH (maps to WARNING transformers)
  description     → Human-readable reason for the ticket
  trigger_type    → AUTO | MANUAL (who raised it)
  health_score    → Health score at the time the ticket was created
  resolved_at     → When engineer marked it done
  resolution_notes → What the engineer did
  outcome         → COMPLETED | REPAIRED | REPLACED | MONITORED
  dedup_key       → Prevents duplicate open tickets for same transformer+type
"""

from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import String, Text, Boolean, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, UUIDMixin, TimestampMixin


class MaintenanceTicket(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "maintenance_tickets"

    # ── Which transformer this ticket is for ─────────────────────────────────
    transformer_id: Mapped[str] = mapped_column(
        String(64),   # stored as string UUID to avoid UUID dialect issues
        nullable=False,
        index=True,
    )

    # ── Ticket state ──────────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="OPEN",   # OPEN | RESOLVED
        index=True,
    )

    priority: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="HIGH",   # CRITICAL | HIGH
    )

    # ── Content ───────────────────────────────────────────────────────────────
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    trigger_type: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="AUTO",   # AUTO | MANUAL
    )

    # Health score at the moment the ticket was raised
    health_score: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )

    # ── Resolution ────────────────────────────────────────────────────────────
    resolved_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    outcome: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # ── Deduplication ─────────────────────────────────────────────────────────
    # Prevents creating a new OPEN ticket for the same transformer+priority
    # while one is already open.
    # Format: "AUTO:CRITICAL:<transformer_id>" or "AUTO:HIGH:<transformer_id>"
    dedup_key: Mapped[Optional[str]] = mapped_column(
        String(256),
        nullable=True,
        unique=True,      # DB-level uniqueness enforced
        index=True,
    )
