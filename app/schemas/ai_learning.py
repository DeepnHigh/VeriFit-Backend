from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AILearningQuestionBase(BaseModel):
    question_text: str
    display_order: int = 0

class AILearningQuestionCreate(AILearningQuestionBase):
    pass

class AILearningQuestionResponse(AILearningQuestionBase):
    id: str
    
    class Config:
        from_attributes = True

class JobSeekerAILearningResponseBase(BaseModel):
    answer: str

class JobSeekerAILearningResponseCreate(JobSeekerAILearningResponseBase):
    pass

class JobSeekerAILearningResponseResponse(JobSeekerAILearningResponseBase):
    id: str
    job_seeker_id: str
    question_id: str
    response_date: datetime
    
    class Config:
        from_attributes = True

class JobSeekerAIAgentBase(BaseModel):
    ai_agent_completion_percentage: float = 0.0

class JobSeekerAIAgentCreate(JobSeekerAIAgentBase):
    job_seeker_id: str

class JobSeekerAIAgentResponse(JobSeekerAIAgentBase):
    id: str
    job_seeker_id: str
    
    class Config:
        from_attributes = True
