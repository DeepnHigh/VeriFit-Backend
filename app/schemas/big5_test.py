from pydantic import BaseModel
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from decimal import Decimal

class Big5TestResultBase(BaseModel):
    # Big5 주요 차원 점수 (0-100 스케일)
    openness_score: Decimal
    conscientiousness_score: Decimal
    extraversion_score: Decimal
    agreeableness_score: Decimal
    neuroticism_score: Decimal
    
    # Big5 결과 레벨 (high, neutral, low)
    openness_level: str
    conscientiousness_level: str
    extraversion_level: str
    agreeableness_level: str
    neuroticism_level: str
    
    # 세부 특성 점수 (각 차원당 6개)
    openness_facets: Optional[Dict[str, Any]] = None
    conscientiousness_facets: Optional[Dict[str, Any]] = None
    extraversion_facets: Optional[Dict[str, Any]] = None
    agreeableness_facets: Optional[Dict[str, Any]] = None
    neuroticism_facets: Optional[Dict[str, Any]] = None
    
    # 전문적인 해석 결과
    interpretations: Optional[Dict[str, Any]] = None
    raw_scores: Optional[Dict[str, Any]] = None

class Big5TestResultCreate(Big5TestResultBase):
    job_seeker_id: str

class Big5TestResultResponse(Big5TestResultBase):
    id: UUID
    job_seeker_id: UUID
    test_date: datetime
    
    class Config:
        from_attributes = True


class Big5TestResultUpdate(BaseModel):
    # 업데이트는 부분 업데이트를 허용
    openness_score: Optional[Decimal] = None
    conscientiousness_score: Optional[Decimal] = None
    extraversion_score: Optional[Decimal] = None
    agreeableness_score: Optional[Decimal] = None
    neuroticism_score: Optional[Decimal] = None

    openness_level: Optional[str] = None
    conscientiousness_level: Optional[str] = None
    extraversion_level: Optional[str] = None
    agreeableness_level: Optional[str] = None
    neuroticism_level: Optional[str] = None

    openness_facets: Optional[Dict[str, Any]] = None
    conscientiousness_facets: Optional[Dict[str, Any]] = None
    extraversion_facets: Optional[Dict[str, Any]] = None
    agreeableness_facets: Optional[Dict[str, Any]] = None
    neuroticism_facets: Optional[Dict[str, Any]] = None

    interpretations: Optional[Dict[str, Any]] = None
    raw_scores: Optional[Dict[str, Any]] = None
