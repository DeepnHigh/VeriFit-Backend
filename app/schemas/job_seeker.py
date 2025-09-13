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
    id: uuid.UUID
    job_seeker_id: uuid.UUID
    uploaded_at: datetime
    
    class Config:
        from_attributes = True

# Big5 성격검사 결과 스키마
class Big5TestResultForMyPage(BaseModel):
    id: uuid.UUID
    test_date: datetime
    openness_score: Decimal
    conscientiousness_score: Decimal
    extraversion_score: Decimal
    agreeableness_score: Decimal
    neuroticism_score: Decimal
    openness_level: str
    conscientiousness_level: str
    extraversion_level: str
    agreeableness_level: str
    neuroticism_level: str
    interpretations: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True

# AI 학습 질문 스키마
class AILearningQuestionForMyPage(BaseModel):
    id: uuid.UUID
    question_category: str
    question_text: str
    display_order: int
    
    class Config:
        from_attributes = True

# AI 학습 응답 스키마 (질문 포함)
class AILearningResponseForMyPage(BaseModel):
    id: uuid.UUID
    answer_text: str
    response_date: datetime
    question: AILearningQuestionForMyPage
    
    class Config:
        from_attributes = True

# 마이페이지 전체 응답 스키마
class JobSeekerMyPageResponse(JobSeekerBase):
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
    
    # 추가 관련 데이터
    big5_test_results: List[Big5TestResultForMyPage] = []
    ai_learning_responses: List[AILearningResponseForMyPage] = []
    documents: List[JobSeekerDocumentResponse] = []
    
    class Config:
        from_attributes = True
