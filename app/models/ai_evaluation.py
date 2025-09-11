from sqlalchemy import Column, String, Text, DateTime, ForeignKey, DECIMAL
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database.database import Base

class AIEvaluation(Base):
    __tablename__ = "ai_evaluations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"), nullable=False)
    # 순위 페이지
    hard_score = Column(DECIMAL(5,2), nullable=False)  # 0.00 ~ 100.00
    soft_score = Column(DECIMAL(5,2), nullable=False)  # 0.00 ~ 100.00
    total_score = Column(DECIMAL(5,2), nullable=False)  # 0.00 ~ 100.00
    ai_summary = Column(Text, nullable=False)  # 총평
    # 상세보기 페이지
    hard_detail_scores = Column(JSONB)  # 하드 스킬 상세 분석 점수
    soft_detail_scores = Column(JSONB)  # 소프트 스킬 상세 분석 점수
    strengths_content = Column(Text)  # 강점 - 내용
    strengths_opinion = Column(Text)  # 강점 - AI면접관 의견
    strengths_evidence = Column(Text)  # 강점 - 근거
    concerns_content = Column(Text)  # 우려사항 - 내용
    concerns_opinion = Column(Text)  # 우려사항 - AI면접관 의견
    concerns_evidence = Column(Text)  # 우려사항 - 근거
    followup_content = Column(Text)  # 후속검증 제안 - 내용
    followup_opinion = Column(Text)  # 후속검증 제안 - AI면접관 의견
    followup_evidence = Column(Text)  # 후속검증 제안 - 근거
    final_opinion = Column(Text)  # AI 면접관 최종 의견
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 관계 설정
    application = relationship("Application", back_populates="ai_evaluations")