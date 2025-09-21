from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime

class ApplicationInfo(BaseModel):
    applications_id: str
    user_id: Optional[str] = None
    candidate_name: Optional[str] = None
    applied_at: Optional[str] = None
    stage: Optional[str] = None
    overall_score: Optional[int] = None
    hard_score: Optional[float] = None
    soft_score: Optional[float] = None
    ai_summary: Optional[str] = None
    evaluated_at: Optional[str] = None

class JobPostingInfo(BaseModel):
    id: str
    title: str
    status: str
    eval_status: Optional[str] = None
    created_at: Optional[str] = None
    hard_skills: List[Any] = []
    soft_skills: List[Any] = []

class AIOverallReportInfo(BaseModel):
    total_applications: Optional[int] = None
    ai_evaluated_count: Optional[int] = None
    ai_recommended_count: Optional[int] = None
    overall_review: str = ""
    created_at: Optional[str] = None

class CountsInfo(BaseModel):
    total: int
    interviewed: int
    offered: int
    rejected: int

class RecruitmentStatusResponse(BaseModel):
    status: int
    success: bool
    data: dict

class RecruitmentStatusData(BaseModel):
    job_posting: JobPostingInfo
    applications: List[ApplicationInfo]
    ai_overall_report: AIOverallReportInfo
    counts: CountsInfo
