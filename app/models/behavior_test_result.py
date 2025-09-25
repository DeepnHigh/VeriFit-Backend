from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
from app.database.database import Base


class BehaviorTestResult(Base):
    __tablename__ = "behavior_test_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    job_seeker_id = Column(UUID(as_uuid=True), ForeignKey("job_seekers.id"), nullable=False, index=True)
    test_date = Column(DateTime(timezone=True), server_default=func.now())

    # 시나리오 및 선택 정보
    situation_text = Column(String, nullable=False)  # 시나리오 설명 (TEXT 대체: PostgreSQL에선 String=TEXT by default when no length)
    selected_character = Column(String(1), nullable=False)  # 선택한 캐릭터 (A, B, C)

    # 대화 기록 (JSON 형태로 저장)
    conversation_history = Column(JSONB, nullable=False)


