from sqlalchemy import Column, String, DateTime, ForeignKey, DECIMAL
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database.database import Base

class Big5TestResult(Base):
    __tablename__ = "big5_test_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    job_seeker_id = Column(UUID(as_uuid=True), ForeignKey("job_seekers.id"), nullable=False)
    test_date = Column(DateTime(timezone=True), server_default=func.now())
    
    # Big5 주요 차원 점수 (0-100 스케일)
    openness_score = Column(DECIMAL(5,2), nullable=False)  # 개방성 점수
    conscientiousness_score = Column(DECIMAL(5,2), nullable=False)  # 성실성 점수
    extraversion_score = Column(DECIMAL(5,2), nullable=False)  # 외향성 점수
    agreeableness_score = Column(DECIMAL(5,2), nullable=False)  # 우호성 점수
    neuroticism_score = Column(DECIMAL(5,2), nullable=False)  # 신경성 점수
    
    # Big5 결과 레벨 (high, neutral, low)
    openness_level = Column(String(10), nullable=False)  # 개방성 레벨
    conscientiousness_level = Column(String(10), nullable=False)  # 성실성 레벨
    extraversion_level = Column(String(10), nullable=False)  # 외향성 레벨
    agreeableness_level = Column(String(10), nullable=False)  # 우호성 레벨
    neuroticism_level = Column(String(10), nullable=False)  # 신경성 레벨
    
    # 세부 특성 점수 (각 차원당 6개)
    openness_facets = Column(JSONB)  # 개방성 세부 특성 (상상력, 예술성, 감정성, 모험성, 지성, 자유주의)
    conscientiousness_facets = Column(JSONB)  # 성실성 세부 특성 (자기효능감, 체계성, 의무감, 성취추구, 자기통제, 신중함)
    extraversion_facets = Column(JSONB)  # 외향성 세부 특성 (친화성, 사교성, 주장성, 활동성, 자극추구, 쾌활함)
    agreeableness_facets = Column(JSONB)  # 우호성 세부 특성 (신뢰, 도덕성, 이타성, 협력, 겸손, 공감)
    neuroticism_facets = Column(JSONB)  # 신경성 세부 특성 (불안, 분노, 우울, 자의식, 무절제, 취약성)
    
    # 전문적인 해석 결과
    interpretations = Column(JSONB)  # 전문적인 해석 텍스트 (한국어/영어)
    raw_scores = Column(JSONB)  # 원본 점수 데이터
    
    # 관계 설정
    job_seeker = relationship("JobSeeker", back_populates="big5_test_results")
