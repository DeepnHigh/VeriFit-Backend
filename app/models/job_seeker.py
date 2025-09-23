from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer, Boolean, Enum, DECIMAL
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database.database import Base

class JobSeeker(Base):
    __tablename__ = "job_seekers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    full_name = Column(String(100), nullable=False)
    phone = Column(String(20))
    email = Column(String(255))
    profile_picture = Column(String(500))
    bio = Column(Text)  # 자기소개/프로필 소개
    total_experience_years = Column(Integer)  # 총 경력 년수
    company_name = Column(String(200))  # 최근 직장
    education_level = Column(Enum('high_school', 'associate', 'bachelor', 'master', 'phd', name='education_level_enum'))
    university = Column(String(200))  # 대학교명
    major = Column(String(100))  # 전공
    graduation_year = Column(Integer)  # 졸업년도
    github_repositories = Column(JSONB)  # GitHub 레포지토리 URL 리스트
    github_histories = Column(JSONB)  # GitHub 활동 요약 저장용
    portfolios = Column(JSONB)  # 포트폴리오
    resumes = Column(JSONB)  # 이력서
    awards = Column(JSONB)  # 수상경력 리스트
    certificates = Column(JSONB)  # 증명서 리스트
    qualifications = Column(JSONB)  # 자격증 리스트
    papers = Column(JSONB)  # 논문 리스트
    cover_letters = Column(JSONB)  # 자기소개서 리스트
    other_documents = Column(JSONB)  # 기타 자료 리스트
    location = Column(String(200))  # 거주지/위치
    profile_completion_percentage = Column(DECIMAL(5,2), default=0.00)  # 프로필 완성도
    last_profile_update = Column(DateTime(timezone=True))  # 마지막 프로필 업데이트
    is_profile_public = Column(Boolean, default=True)  # 프로필 공개 여부
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 생성일시
    full_text = Column(Text)  # 전체 텍스트(LLM/검색용)
    behavior_text = Column(Text)  # 행동검사 텍스트
    big5_text = Column(Text)  # Big5 성격검사 요약 텍스트
    
    # 관계 설정
    user = relationship("User", back_populates="job_seeker")
    applications = relationship("Application", back_populates="job_seeker")
    documents = relationship("JobSeekerDocument", back_populates="job_seeker")
    ai_agent = relationship("JobSeekerAIAgent", back_populates="job_seeker", uselist=False)
    big5_test_results = relationship("Big5TestResult", back_populates="job_seeker")
    ai_learning_answers = relationship("AILearningAnswer", back_populates="job_seeker")
