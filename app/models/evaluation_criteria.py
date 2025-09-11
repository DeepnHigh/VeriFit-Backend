from sqlalchemy import Column, String, Text, ForeignKey, Enum, DECIMAL
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.database.database import Base

class EvaluationCriteria(Base):
    __tablename__ = "evaluation_criteria"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    job_posting_id = Column(UUID(as_uuid=True), ForeignKey("job_postings.id"), nullable=False)
    skill_type = Column(Enum('hard_skill', 'soft_skill', name='skill_type_enum'), nullable=False)
    skill_name = Column(String(100), nullable=False)
    skill_description = Column(Text)
    percentage = Column(DECIMAL(5,2), default=0.00)  # 비중 (0.00 ~ 100.00)
    
    # 관계 설정
    job_posting = relationship("JobPosting", back_populates="evaluation_criteria")