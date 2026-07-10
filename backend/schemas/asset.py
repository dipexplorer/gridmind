from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, List, Any
from datetime import date, datetime
import uuid

# --- Substation Schemas ---
class SubstationBase(BaseModel):
    name: str = Field(..., max_length=128)
    code: str = Field(..., max_length=32)
    voltage_kv: float
    district: Optional[str] = Field(None, max_length=64)
    location: Optional[str] = None # Will accept WKT (Well-Known Text) for PostGIS like 'POINT(78.9629 20.5937)'

class SubstationCreate(SubstationBase):
    pass

class SubstationResponse(SubstationBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    
    @field_validator('location', mode='before')
    def parse_location(cls, v: Any):
        if v is not None:
            try:
                from geoalchemy2.shape import to_shape
                shape = to_shape(v)
                return f"POINT({shape.x} {shape.y})"
            except Exception:
                pass
        return str(v) if v is not None else None

    model_config = ConfigDict(from_attributes=True)

# --- Feeder Schemas ---
class FeederBase(BaseModel):
    name: str = Field(..., max_length=128)
    code: str = Field(..., max_length=32)
    voltage_kv: float = 11.0
    feeder_type: Optional[str] = Field(None, max_length=32)

class FeederCreate(FeederBase):
    substation_id: uuid.UUID

class FeederResponse(FeederBase):
    id: uuid.UUID
    substation_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# --- Transformer Schemas ---
class TransformerBase(BaseModel):
    transformer_code: str = Field(..., max_length=64)
    rated_kva: float
    voltage_hv_kv: Optional[float] = None
    voltage_lv_v: Optional[float] = None
    installation_type: Optional[str] = Field(None, max_length=32)
    cooling_type: Optional[str] = Field("ONAN", max_length=16)
    manufacturer: Optional[str] = Field(None, max_length=64)
    
    location: Optional[str] = None # WKT format 'POINT(lon lat)'
    address_text: Optional[str] = None
    district: Optional[str] = Field(None, max_length=64)
    block: Optional[str] = Field(None, max_length=64)
    is_flood_prone: Optional[bool] = False
    is_high_lightning: Optional[bool] = False
    
    installation_date: Optional[date] = None
    last_oil_test_date: Optional[date] = None
    commissioning_date: Optional[date] = None
    
    num_consumers: Optional[int] = 0
    consumer_category: Optional[str] = Field("MIXED", max_length=32)
    area_criticality: Optional[float] = 1.0
    operational_status: Optional[str] = Field("IN_SERVICE", max_length=32)

    # Real-time fields from live sync
    age_years: Optional[int] = None
    is_metered: Optional[bool] = None
    current_load_kw: Optional[float] = None
    current_load_pct: Optional[float] = None
    current_oil_temp_c: Optional[float] = None
    current_health_score: Optional[int] = None
    current_failure_risk: Optional[float] = None
    current_status: Optional[str] = None
    last_updated: Optional[datetime] = None


class TransformerCreate(TransformerBase):
    feeder_id: Optional[uuid.UUID] = None
    substation_id: Optional[uuid.UUID] = None

class TransformerResponse(TransformerBase):
    id: uuid.UUID
    feeder_id: Optional[uuid.UUID]
    substation_id: Optional[uuid.UUID]
    created_by: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime
    
    @field_validator('location', mode='before')
    def parse_location(cls, v: Any):
        if v is not None:
            try:
                from geoalchemy2.shape import to_shape
                shape = to_shape(v)
                return f"POINT({shape.x} {shape.y})"
            except Exception as e:
                print("GEOMETRY PARSE ERROR:", e, type(v))
                pass
        return str(v) if v is not None else None
    
    model_config = ConfigDict(from_attributes=True)
