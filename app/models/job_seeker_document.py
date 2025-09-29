from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database.database import Base

class JobSeekerDocument(Base):
    __tablename__ = "job_seeker_documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    job_seeker_id = Column(UUID(as_uuid=True), ForeignKey("job_seekers.id"), nullable=False)
    document_type = Column(Enum('portfolio', 'resume', 'award', 'certificate', 'qualification', 'paper', 'cover_letter', 'other', 'github', name='document_type_enum'), nullable=False)
    # 저장된 실제 파일명(유니크)
    file_name = Column(String(255), nullable=False)
    # 사용자가 업로드한 원본 파일명(표시용)
    original_file_name = Column(String(255), nullable=True)
    file_url = Column(String(500), nullable=False)
    file_size = Column(Integer)  # bytes
    mime_type = Column(String(100))  # 타입 (application/pdf)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 관계 설정
    job_seeker = relationship("JobSeeker", back_populates="documents")