from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database.database import Base


class Application(Base):
    __tablename__ = "applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    job_posting_id = Column(UUID(as_uuid=True), ForeignKey("job_postings.id"), nullable=False)
    job_seeker_id = Column(UUID(as_uuid=True), ForeignKey("job_seekers.id"), nullable=False)
    application_status = Column(Enum('submitted', 'under_review', 'ai_evaluated', 'shortlisted', 'rejected', 'hired', name='application_status_enum'), default='submitted')
    applied_at = Column(DateTime(timezone=True), server_default=func.now())
    evaluated_at = Column(DateTime(timezone=True))
    notes = Column(Text)

    # 관계 설정
    job_posting = relationship("JobPosting", back_populates="applications")
    job_seeker = relationship("JobSeeker", back_populates="applications")
    ai_evaluations = relationship("AIEvaluation", back_populates="application")
    ai_interview_messages = relationship("AIInterviewMessage", back_populates="application")


