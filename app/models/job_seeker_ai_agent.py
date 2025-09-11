from sqlalchemy import Column, ForeignKey, DECIMAL
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.database.database import Base

class JobSeekerAIAgent(Base):
    __tablename__ = "job_seeker_ai_agents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    job_seeker_id = Column(UUID(as_uuid=True), ForeignKey("job_seekers.id"), nullable=False)
    ai_agent_completion_percentage = Column(DECIMAL(5,2), default=0.00)  # AI 에이전트 완성도
    
    # 관계 설정
    job_seeker = relationship("JobSeeker", back_populates="ai_agent")