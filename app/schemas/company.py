from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CompanyBase(BaseModel):
    company_name: str
    industry: Optional[str] = None
    company_size: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    founded_year: Optional[int] = None
    employee_count: Optional[int] = None
    headquarters_location: Optional[str] = None
    business_registration_number: Optional[str] = None

class CompanyCreate(CompanyBase):
    user_id: str

class CompanyUpdate(BaseModel):
    company_name: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    founded_year: Optional[int] = None
    employee_count: Optional[int] = None
    headquarters_location: Optional[str] = None
    business_registration_number: Optional[str] = None
    company_status: Optional[str] = None

class CompanyResponse(CompanyBase):
    id: str
    user_id: str
    logo_url: Optional[str] = None
    company_status: str
    created_at: datetime
    
    class Config:
        from_attributes = True
