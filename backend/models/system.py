from sqlalchemy import Column, String, Float, DateTime
from datetime import datetime
from models.base import Base

class SystemSettings(Base):
    __tablename__ = "system_settings"

    id = Column(String(50), primary_key=True, default="default")
    critical_threshold = Column(Float, default=75.0, nullable=False)
    high_threshold = Column(Float, default=55.0, nullable=False)
    medium_threshold = Column(Float, default=35.0, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
