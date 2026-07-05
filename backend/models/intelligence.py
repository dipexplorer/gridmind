from datetime import datetime
from sqlalchemy import String, Numeric, Boolean, ForeignKey, Text, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from typing import Optional

from .base import Base, UUIDMixin, TimestampMixin

class ScoreRunMetadata(Base, UUIDMixin):
    __tablename__ = "score_run_metadata"

    status: Mapped[str] = mapped_column(String(32), default="RUNNING")
    anomalies_detected: Mapped[int] = mapped_column(default=0, nullable=False)
    
    started_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    completed_at: Mapped[Optional[datetime]]

class TransformerScore(Base, UUIDMixin):
    __tablename__ = "transformer_scores"

    transformer_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("transformers.id", ondelete="CASCADE"), nullable=False)
    run_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("score_run_metadata.id"))
    
    anomaly_score: Mapped[Optional[float]] = mapped_column(Numeric(6, 4))
    risk_category: Mapped[str] = mapped_column(String(16), nullable=False)
    
    expected_lifetime_days: Mapped[Optional[int]] = mapped_column(Integer)
    confidence_interval_lower: Mapped[Optional[int]] = mapped_column(Integer)
    confidence_interval_upper: Mapped[Optional[int]] = mapped_column(Integer)
    
    calculated_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

class ShapExplanation(Base, UUIDMixin):
    __tablename__ = "shap_explanations"

    score_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("transformer_scores.id", ondelete="CASCADE"), nullable=False)
    
    feature_name: Mapped[str] = mapped_column(String(64), nullable=False)
    feature_value: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    shap_value: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
