from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer, Boolean, Enum, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database.database import Base

class JobPosting(Base):
    __tablename__ = "job_postings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    title = Column(String(200), nullable=False)
    position_level = Column(Enum('intern', 'junior', 'mid', 'senior', 'lead', 'manager', name='position_level_enum'))
    employment_type = Column(Enum('full_time', 'part_time', 'contract', 'internship', name='employment_type_enum'))
    location = Column(String(200))
    salary_min = Column(Integer)
    salary_max = Column(Integer)
    main_tasks = Column(Text, nullable=False)
    requirements = Column(Text)
    preferred = Column(Text)
    application_deadline = Column(Date)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 관계 설정
    company = relationship("Company", back_populates="job_postings")
    applications = relationship("Application", back_populates="job_posting")
    evaluation_criteria = relationship("EvaluationCriteria", back_populates="job_posting")
    ai_overall_report = relationship("AIOverallReport", back_populates="job_posting", uselist=False)
