from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database.database import Base

class InterviewHighlight(Base):
    __tablename__ = "interview_highlights"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"), nullable=False)
    highlight_text = Column(Text, nullable=False)  # 하이라이트 텍스트
    highlight_reason = Column(Text, nullable=True)  # 하이라이트 이유
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 관계 설정
    application = relationship("Application", back_populates="interview_highlights")