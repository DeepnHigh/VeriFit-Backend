from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database.database import Base

class JobSeekerAILearningResponse(Base):
    __tablename__ = "job_seeker_ai_learning_responses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    job_seeker_id = Column(UUID(as_uuid=True), ForeignKey("job_seekers.id"), nullable=False)
    question_id = Column(UUID(as_uuid=True), ForeignKey("ai_learning_questions.id"), nullable=False)
    answer_text = Column(Text, nullable=False)  # 답변 내용
    response_date = Column(DateTime(timezone=True), server_default=func.now())
    
    # 관계 설정
    job_seeker = relationship("JobSeeker", back_populates="ai_learning_responses")
    question = relationship("AILearningQuestion")