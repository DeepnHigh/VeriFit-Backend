from pydantic import BaseModel, Field
from pydantic.config import ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID

class AILearningQuestionBase(BaseModel):
    question_text: str
    display_order: int = 0

class AILearningQuestionCreate(AILearningQuestionBase):
    pass

class AILearningQuestionResponse(AILearningQuestionBase):
    id: UUID
    
    class Config:
        from_attributes = True

class JobSeekerAILearningResponseBase(BaseModel):
    answer: str

class JobSeekerAILearningResponseCreate(JobSeekerAILearningResponseBase):
    pass

class JobSeekerAILearningResponseResponse(BaseModel):
    id: UUID
    job_seeker_id: UUID
    question_id: UUID
    answer: str = Field(validation_alias="answer_text", serialization_alias="answer")
    response_date: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class JobSeekerAIAgentBase(BaseModel):
    ai_agent_completion_percentage: float = 0.0

class JobSeekerAIAgentCreate(JobSeekerAIAgentBase):
    job_seeker_id: str

class JobSeekerAIAgentResponse(JobSeekerAIAgentBase):
    id: str
    job_seeker_id: str
    
    class Config:
        from_attributes = True
