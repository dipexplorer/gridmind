from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional

from .base import Base, UUIDMixin, TimestampMixin

class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # 'ADMIN' | 'ENGINEER'
    full_name: Mapped[Optional[str]] = mapped_column(String(128))
    region: Mapped[Optional[str]] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
