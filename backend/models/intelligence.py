from datetime import datetime
from sqlalchemy import String, Numeric, Boolean, ForeignKey, Text, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from typing import Optional

from .base import Base, UUIDMixin, TimestampMixin

class ScoreRunMetadata(Base, UUIDMixin):
    __tablename__ = "score_run_metadata"

    run_type: Mapped[str] = mapped_column(String(32), nullable=False)
    trigger_reason: Mapped[Optional[str]] = mapped_column(Text)
    
    transformers_scored: Mapped[int] = mapped_column(default=0, nullable=False)
    transformers_failed: Mapped[int] = mapped_column(default=0, nullable=False)
    
    newly_critical: Mapped[Optional[int]] = mapped_column(default=0)
    newly_high: Mapped[Optional[int]] = mapped_column(default=0)
    newly_healthy: Mapped[Optional[int]] = mapped_column(default=0)
    avg_score_delta: Mapped[Optional[float]] = mapped_column(Numeric(6, 4))
    
    duration_seconds: Mapped[Optional[float]] = mapped_column(Numeric(8, 2))
    model_versions: Mapped[Optional[dict]] = mapped_column(JSONB)
    ml_mode: Mapped[Optional[str]] = mapped_column(String(32), default='FULL')
    
    started_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    completed_at: Mapped[Optional[datetime]]

class TransformerScore(Base, UUIDMixin):
    __tablename__ = "transformer_scores"

    transformer_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("transformers.id", ondelete="CASCADE"), nullable=False)
    score_run_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=True), ForeignKey("score_run_metadata.id"))
    
    survival_prob_30d: Mapped[Optional[float]] = mapped_column(Numeric(5, 4))
    survival_prob_60d: Mapped[Optional[float]] = mapped_column(Numeric(5, 4))
    survival_prob_90d: Mapped[Optional[float]] = mapped_column(Numeric(5, 4))
    
    anomaly_score: Mapped[Optional[float]] = mapped_column(Numeric(6, 4))
    is_anomalous: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    
    failure_risk_score: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    priority_score: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))
    risk_tier: Mapped[str] = mapped_column(String(16), nullable=False)
    
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    scored_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

class ShapExplanation(Base, UUIDMixin):
    __tablename__ = "shap_explanations"

    transformer_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("transformers.id", ondelete="CASCADE"), nullable=False)
    score_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("transformer_scores.id", ondelete="CASCADE"), nullable=False)
    
    top_factors: Mapped[dict] = mapped_column(JSONB, nullable=False)
    model_version: Mapped[Optional[str]] = mapped_column(String(32))
    
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

class ModelRegistry(Base, UUIDMixin):
    __tablename__ = "model_registry"

    model_type: Mapped[str] = mapped_column(String(32), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    version_tag: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    
    trained_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    training_samples: Mapped[int] = mapped_column(nullable=False)
    event_count: Mapped[Optional[int]]
    training_data_hash: Mapped[Optional[str]] = mapped_column(String(64))
    
    c_index: Mapped[Optional[float]] = mapped_column(Numeric(5, 4))
    brier_score_90d: Mapped[Optional[float]] = mapped_column(Numeric(5, 4))
    ph_test_pvalue: Mapped[Optional[float]] = mapped_column(Numeric(6, 4))
    contamination_rate: Mapped[Optional[float]] = mapped_column(Numeric(5, 4))
    
    artifact_path: Mapped[str] = mapped_column(Text, nullable=False)
    feature_names: Mapped[Optional[dict]] = mapped_column(JSONB)
    hyperparameters: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
