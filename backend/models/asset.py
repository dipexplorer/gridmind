from datetime import date
from sqlalchemy import String, Numeric, Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geography
from typing import Optional

from .base import Base, UUIDMixin, TimestampMixin

class Substation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "substations"

    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    voltage_kv: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    district: Mapped[Optional[str]] = mapped_column(String(64))
    # Using Geography type for PostGIS POINT with SRID 4326 (WGS 84)
    location: Mapped[Optional[str]] = mapped_column(Geography(geometry_type='POINT', srid=4326))
    
    feeders = relationship("Feeder", back_populates="substation")
    transformers = relationship("Transformer", back_populates="substation")

class Feeder(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "feeders"

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    substation_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("substations.id", ondelete="RESTRICT"), nullable=False)
    voltage_kv: Mapped[float] = mapped_column(Numeric(6, 2), default=11.0, nullable=False)
    feeder_type: Mapped[Optional[str]] = mapped_column(String(32))  # 'OVERHEAD', 'UNDERGROUND'

    substation = relationship("Substation", back_populates="feeders")
    transformers = relationship("Transformer", back_populates="feeder")

class Transformer(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "transformers"

    transformer_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    feeder_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("feeders.id", ondelete="SET NULL"))
    substation_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("substations.id", ondelete="SET NULL"))
    
    rated_kva: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    voltage_hv_kv: Mapped[Optional[float]] = mapped_column(Numeric(6, 2))
    voltage_lv_v: Mapped[Optional[float]] = mapped_column(Numeric(6, 2))
    installation_type: Mapped[Optional[str]] = mapped_column(String(32))  # 'POLE', 'PAD', 'GROUND', 'UNKNOWN'
    cooling_type: Mapped[Optional[str]] = mapped_column(String(16), default='ONAN')
    manufacturer: Mapped[Optional[str]] = mapped_column(String(64))
    
    location: Mapped[str] = mapped_column(Geography(geometry_type='POINT', srid=4326), nullable=False)
    address_text: Mapped[Optional[str]] = mapped_column(Text)
    district: Mapped[Optional[str]] = mapped_column(String(64))
    block: Mapped[Optional[str]] = mapped_column(String(64))
    is_flood_prone: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    is_high_lightning: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    
    installation_date: Mapped[date] = mapped_column(nullable=False)
    last_oil_test_date: Mapped[Optional[date]]
    commissioning_date: Mapped[Optional[date]]
    
    num_consumers: Mapped[int] = mapped_column(default=0, nullable=False)
    consumer_category: Mapped[Optional[str]] = mapped_column(String(32), default='MIXED')
    area_criticality: Mapped[Optional[float]] = mapped_column(Numeric(3, 2), default=1.0)
    
    operational_status: Mapped[str] = mapped_column(String(32), default='IN_SERVICE', nullable=False)
    
    created_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    feeder = relationship("Feeder", back_populates="transformers")
    substation = relationship("Substation", back_populates="transformers")
    # creator = relationship("User") # can add later if needed
