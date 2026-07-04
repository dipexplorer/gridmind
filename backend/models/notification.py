from datetime import datetime
from sqlalchemy import String, Boolean, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.sql import func
from typing import Optional
from ipaddress import IPv4Address, IPv6Address
from typing import Union

from .base import Base, UUIDMixin, TimestampMixin

class Notification(Base, UUIDMixin):
    __tablename__ = "notifications"

    user_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    alert_type: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    
    resource_type: Mapped[Optional[str]] = mapped_column(String(32))
    resource_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True))
    
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[Optional[datetime]]
    
    dedup_key: Mapped[Optional[str]] = mapped_column(String(256), unique=True)
    
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

class AuditLog(Base, UUIDMixin):
    __tablename__ = "audit_log"

    user_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_type: Mapped[Optional[str]] = mapped_column(String(64))
    resource_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True))
    
    old_values: Mapped[Optional[dict]] = mapped_column(JSONB)
    new_values: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    ip_address: Mapped[Optional[Union[IPv4Address, IPv6Address]]] = mapped_column(INET)
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
