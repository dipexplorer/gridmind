from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
import uuid
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: str = "viewer"
    is_active: bool = True

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
