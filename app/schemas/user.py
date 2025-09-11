from pydantic import BaseModel, EmailStr
import uuid
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    user_type: str

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None

class UserResponse(UserBase):
    id: uuid.UUID
    is_active: bool
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    email: EmailStr
    password: str
