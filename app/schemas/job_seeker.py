from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
import uuid

class JobSeekerBase(BaseModel):
    full_name: str
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    bio: Optional[str] = None
    total_experience_years: Optional[int] = None
    company_name: Optional[str] = None
    education_level: Optional[str] = None
    university: Optional[str] = None
    major: Optional[str] = None
    graduation_year: Optional[int] = None
    location: Optional[str] = None
    is_profile_public: bool = True

class JobSeekerCreate(JobSeekerBase):
    user_id: str

class JobSeekerUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    bio: Optional[str] = None
    total_experience_years: Optional[int] = None
    company_name: Optional[str] = None
    education_level: Optional[str] = None
    university: Optional[str] = None
    major: Optional[str] = None
    graduation_year: Optional[int] = None
    location: Optional[str] = None
    is_profile_public: Optional[bool] = None

class JobSeekerResponse(JobSeekerBase):
    id: uuid.UUID
    user_id: uuid.UUID
    profile_picture: Optional[str] = None
    github_repositories: Optional[List[Dict[str, Any]]] = None
    portfolios: Optional[List[Dict[str, Any]]] = None
    resumes: Optional[List[Dict[str, Any]]] = None
    awards: Optional[List[Dict[str, Any]]] = None
    certificates: Optional[List[Dict[str, Any]]] = None
    qualifications: Optional[List[Dict[str, Any]]] = None
    papers: Optional[List[Dict[str, Any]]] = None
    cover_letters: Optional[List[Dict[str, Any]]] = None
    other_documents: Optional[List[Dict[str, Any]]] = None
    profile_completion_percentage: Decimal
    last_profile_update: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class JobSeekerDocumentBase(BaseModel):
    document_type: str
    file_name: str
    file_url: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None

class JobSeekerDocumentCreate(JobSeekerDocumentBase):
    job_seeker_id: str

class JobSeekerDocumentResponse(JobSeekerDocumentBase):
    id: str
    job_seeker_id: str
    uploaded_at: datetime
    
    class Config:
        from_attributes = True
