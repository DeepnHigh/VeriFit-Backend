from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date

class JobPostingBase(BaseModel):
    title: str
    position_level: Optional[str] = None
    employment_type: Optional[str] = None
    location: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    main_tasks: str
    requirements: Optional[str] = None
    preferred: Optional[str] = None
    application_deadline: Optional[date] = None

class JobPostingCreate(JobPostingBase):
    company_id: str

class JobPostingUpdate(BaseModel):
    title: Optional[str] = None
    position_level: Optional[str] = None
    employment_type: Optional[str] = None
    location: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    main_tasks: Optional[str] = None
    requirements: Optional[str] = None
    preferred: Optional[str] = None
    application_deadline: Optional[date] = None
    is_active: Optional[bool] = None

class JobPostingResponse(JobPostingBase):
    id: str
    company_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class EvaluationCriteriaBase(BaseModel):
    skill_type: str
    skill_name: str
    skill_description: Optional[str] = None
    percentage: float

class EvaluationCriteriaCreate(EvaluationCriteriaBase):
    job_posting_id: str

class EvaluationCriteriaResponse(EvaluationCriteriaBase):
    id: str
    job_posting_id: str
    
    class Config:
        from_attributes = True
