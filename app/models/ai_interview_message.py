from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.database.database import Base

class AIInterviewMessage(Base):
    __tablename__ = "ai_interview_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"), nullable=False)
    sender = Column(Enum('interviewer_ai', 'candidate_ai', name='sender_enum'), nullable=False)  # 발화자
    message_type = Column(Enum('question', 'answer', 'system', 'other', name='message_type_enum'), default='other')
    content = Column(Text, nullable=False)  # 메시지 본문
    turn_number = Column(Integer, nullable=False)  # 대화 턴 번호 (1=질문, 2=답변, 3=질문...)
    highlight_turns = Column(JSONB)  # 하이라이트 턴 리스트 (예: [3,4,7,8])
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 관계 설정
    application = relationship("Application", back_populates="ai_interview_messages")