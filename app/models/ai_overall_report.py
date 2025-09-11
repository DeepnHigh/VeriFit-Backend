from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database.database import Base

class AIOverallReport(Base):
    __tablename__ = "ai_overall_report"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    job_posting_id = Column(UUID(as_uuid=True), ForeignKey("job_postings.id"), nullable=False)
    # 채용 현황 통계 (계산 불가능한 값들만 저장)
    total_applications = Column(Integer, nullable=False)  # 총 지원자 수
    ai_evaluated_count = Column(Integer, nullable=False)  # AI 평가 완료 수  
    ai_recommended_count = Column(Integer, nullable=False)  # AI면접관 추천 수
    # AI 분석 결과
    hard_skill_evaluation = Column(JSONB, nullable=False)  # 하드스킬 평가 항목 및 내용
    soft_skill_evaluation = Column(JSONB, nullable=False)  # 소프트스킬 평가 항목 및 내용
    overall_review = Column(Text, nullable=False)  # AI면접관 총평
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 관계 설정
    job_posting = relationship("JobPosting", back_populates="ai_overall_report")