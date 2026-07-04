from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
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
    
    location: str # WKT format 'POINT(lon lat)'
    address_text: Optional[str] = None
    district: Optional[str] = Field(None, max_length=64)
    block: Optional[str] = Field(None, max_length=64)
    is_flood_prone: bool = False
    is_high_lightning: bool = False
    
    installation_date: date
    last_oil_test_date: Optional[date] = None
    commissioning_date: Optional[date] = None
    
    num_consumers: int = 0
    consumer_category: str = Field("MIXED", max_length=32)
    area_criticality: float = 1.0
    operational_status: str = Field("IN_SERVICE", max_length=32)

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
    
    model_config = ConfigDict(from_attributes=True)
