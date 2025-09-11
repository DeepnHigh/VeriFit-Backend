from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class ApplicationBase(BaseModel):
    job_posting_id: str
    job_seeker_id: str
    notes: Optional[str] = None

class ApplicationCreate(ApplicationBase):
    pass

class ApplicationUpdate(BaseModel):
    application_status: Optional[str] = None
    notes: Optional[str] = None

class ApplicationResponse(ApplicationBase):
    id: str
    application_status: str
    applied_at: datetime
    evaluated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class AIEvaluationBase(BaseModel):
    hard_score: float
    soft_score: float
    total_score: float
    ai_summary: str
    hard_detail_scores: Optional[Dict[str, Any]] = None
    soft_detail_scores: Optional[Dict[str, Any]] = None
    strengths_content: Optional[str] = None
    strengths_opinion: Optional[str] = None
    strengths_evidence: Optional[str] = None
    concerns_content: Optional[str] = None
    concerns_opinion: Optional[str] = None
    concerns_evidence: Optional[str] = None
    followup_content: Optional[str] = None
    followup_opinion: Optional[str] = None
    followup_evidence: Optional[str] = None
    final_opinion: Optional[str] = None

class AIEvaluationCreate(AIEvaluationBase):
    application_id: str

class AIEvaluationResponse(AIEvaluationBase):
    id: str
    application_id: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class AIInterviewMessageBase(BaseModel):
    sender: str
    message_type: str = "other"
    content: str
    turn_number: int
    highlight_turns: Optional[Dict[str, Any]] = None

class AIInterviewMessageCreate(AIInterviewMessageBase):
    application_id: str

class AIInterviewMessageResponse(AIInterviewMessageBase):
    id: str
    application_id: str
    created_at: datetime
    
    class Config:
        from_attributes = True
