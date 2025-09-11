from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import DECIMAL
import uuid
from app.database.database import Base


class AptitudeTestResult(Base):
    __tablename__ = "aptitude_test_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    job_seeker_id = Column(UUID(as_uuid=True), ForeignKey("job_seekers.id"), nullable=False)
    test_date = Column(DateTime(timezone=True), server_default=func.now())
    test_duration_minutes = Column(Integer)
    realistic_score = Column(DECIMAL(5, 2), nullable=False)
    investigative_score = Column(DECIMAL(5, 2), nullable=False)
    artistic_score = Column(DECIMAL(5, 2), nullable=False)
    social_score = Column(DECIMAL(5, 2), nullable=False)
    enterprising_score = Column(DECIMAL(5, 2), nullable=False)
    conventional_score = Column(DECIMAL(5, 2), nullable=False)
    overall_analysis = Column(Text)

    # 관계 설정
    job_seeker = relationship("JobSeeker", back_populates="aptitude_test_results")


