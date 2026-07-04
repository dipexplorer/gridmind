from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

class ScoreRunMetadataBase(BaseModel):
    run_type: str = Field(..., max_length=32)
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str = Field(..., max_length=32)
    transformers_scored: int = 0
    anomalies_detected: int = 0
    execution_time_sec: Optional[float] = None
    model_version: Optional[str] = Field(None, max_length=64)
    error_log: Optional[str] = None

class ScoreRunMetadataResponse(ScoreRunMetadataBase):
    id: uuid.UUID
    
    model_config = ConfigDict(from_attributes=True)

class TransformerScoreBase(BaseModel):
    health_score: float
    risk_category: str = Field(..., max_length=16)
    anomaly_flag: bool = False
    confidence_score: Optional[float] = None

class TransformerScoreResponse(TransformerScoreBase):
    id: uuid.UUID
    transformer_id: uuid.UUID
    run_id: uuid.UUID
    calculated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ShapExplanationBase(BaseModel):
    feature_name: str = Field(..., max_length=64)
    shap_value: float
    feature_value: Optional[float] = None

class ShapExplanationResponse(ShapExplanationBase):
    id: uuid.UUID
    score_id: uuid.UUID
    
    model_config = ConfigDict(from_attributes=True)
