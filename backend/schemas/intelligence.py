from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

class ScoreRunMetadataBase(BaseModel):
    status: str = Field(..., max_length=32)
    anomalies_detected: int = 0
    started_at: datetime
    completed_at: Optional[datetime] = None
    
class ScoreRunMetadataResponse(ScoreRunMetadataBase):
    id: uuid.UUID
    
    model_config = ConfigDict(from_attributes=True)

class TransformerScoreBase(BaseModel):
    anomaly_score: Optional[float] = None
    risk_category: str = Field(..., max_length=16)
    expected_lifetime_days: Optional[int] = None
    confidence_interval_lower: Optional[int] = None
    confidence_interval_upper: Optional[int] = None

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
