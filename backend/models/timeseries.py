from datetime import datetime
from sqlalchemy import String, Numeric, Boolean, ForeignKey, Text, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from typing import Optional

from .base import Base, TimestampMixin

class Complaint(Base, TimestampMixin):
    __tablename__ = "complaints"

    # Using id as primary key and time as an indexed column for standard Postgres table.
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    transformer_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("transformers.id", ondelete="CASCADE"), nullable=False)
    
    complaint_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String(32), default='CALL_CENTER')
    severity: Mapped[Optional[int]] = mapped_column(Integer, default=3)
    
    description: Mapped[Optional[str]] = mapped_column(Text)
    resolved: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    resolution_time_hrs: Mapped[Optional[float]] = mapped_column(Numeric(6, 2))

class LoadReading(Base):
    __tablename__ = "load_readings"
    
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    transformer_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("transformers.id", ondelete="CASCADE"), primary_key=True)
    
    load_kw: Mapped[Optional[float]] = mapped_column(Numeric(8, 2))
    load_kvar: Mapped[Optional[float]] = mapped_column(Numeric(8, 2))
    load_percentage: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    voltage_lv: Mapped[Optional[float]] = mapped_column(Numeric(6, 2))
    current_a: Mapped[Optional[float]] = mapped_column(Numeric(8, 2))
    temperature_c: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    
    source: Mapped[Optional[str]] = mapped_column(String(32), default='MANUAL')
