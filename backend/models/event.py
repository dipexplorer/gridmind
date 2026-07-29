from datetime import date, datetime
from sqlalchemy import String, Numeric, Boolean, ForeignKey, Text, ARRAY, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from typing import Optional

from .base import Base, UUIDMixin, TimestampMixin

class MaintenanceLog(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "maintenance_logs"

    transformer_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("transformers.id", ondelete="CASCADE"), nullable=False)
    
    maintenance_date: Mapped[date] = mapped_column(nullable=False)
    maintenance_type: Mapped[str] = mapped_column(String(32), nullable=False)
    
    components_replaced: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text))
    work_description: Mapped[Optional[str]] = mapped_column(Text)
    findings: Mapped[Optional[str]] = mapped_column(Text)
    
    oil_bdv_kv: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    winding_resistance: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))
    insulation_megohm: Mapped[Optional[float]] = mapped_column(Numeric(8, 2))
    
    engineer_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    crew_size: Mapped[Optional[int]]
    duration_hours: Mapped[Optional[float]] = mapped_column(Numeric(4, 1))
    
    outcome: Mapped[Optional[str]] = mapped_column(String(32), default='COMPLETED')
    next_maintenance_due: Mapped[Optional[date]]
    
    # transformer = relationship("Transformer")
    # engineer = relationship("User")

class FailureEvent(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "failure_events"

    transformer_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("transformers.id", ondelete="CASCADE"), nullable=False)
    
    failure_date: Mapped[datetime] = mapped_column(nullable=False)
    failure_type: Mapped[Optional[str]] = mapped_column(String(64))
    
    outage_duration_hrs: Mapped[Optional[float]] = mapped_column(Numeric(6, 2))
    consumers_affected: Mapped[Optional[int]]
    
    cause_identified: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    cause_description: Mapped[Optional[str]] = mapped_column(Text)
    
    restoration_date: Mapped[Optional[datetime]]
    replacement_cost_inr: Mapped[Optional[float]] = mapped_column(Numeric(12, 2))
    
    reported_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
