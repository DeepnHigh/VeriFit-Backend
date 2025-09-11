from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from decimal import Decimal

class AptitudeTestResultBase(BaseModel):
    test_duration_minutes: Optional[int] = None
    realistic_score: Decimal
    investigative_score: Decimal
    artistic_score: Decimal
    social_score: Decimal
    enterprising_score: Decimal
    conventional_score: Decimal
    overall_analysis: Optional[str] = None

class AptitudeTestResultCreate(AptitudeTestResultBase):
    job_seeker_id: str

class AptitudeTestResultResponse(AptitudeTestResultBase):
    id: str
    job_seeker_id: str
    test_date: datetime
    
    class Config:
        from_attributes = True
