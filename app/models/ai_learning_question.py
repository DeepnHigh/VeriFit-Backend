from sqlalchemy import Column, String, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.database.database import Base

class AILearningQuestion(Base):
    __tablename__ = "ai_learning_questions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    question_text = Column(Text, nullable=False)  # 질문 내용
    display_order = Column(Integer, default=0)  # 표시 순서