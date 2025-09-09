from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.database import Base

class Applicant(Base):
    __tablename__ = "applicants"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    bio = Column(Text)
    phone = Column(String)
    address = Column(String)
    education = Column(String)
    experience = Column(Text)
    skills = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 관계 설정
    user = relationship("User", back_populates="applicant")
    documents = relationship("Document", back_populates="applicant")
    aptitude_tests = relationship("AptitudeTest", back_populates="applicant")
    behavior_tests = relationship("BehaviorTest", back_populates="applicant")
    own_qnas = relationship("OwnQnA", back_populates="applicant")
