from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.database.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    user_type = Column(String, nullable=False)  # "jobseeker" or "company"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 관계 설정
    job_seeker = relationship("JobSeeker", back_populates="user", uselist=False)
    company = relationship("Company", back_populates="user", uselist=False)

