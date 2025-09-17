from sqlalchemy.orm import Session
from app.models.big5_test_result import Big5TestResult
from app.schemas.big5_test import Big5TestResultCreate
from typing import Optional
import uuid

class Big5TestService:
    def __init__(self, db: Session):
        self.db = db

    def get_big5_test_result(self, user_id: str) -> Optional[Big5TestResult]:
        """지원자 Big5 성격검사 결과 조회"""
        return self.db.query(Big5TestResult).filter(
            Big5TestResult.job_seeker_id == user_id
        ).first()

    def save_big5_result(self, data: Big5TestResultCreate) -> Big5TestResult:
        """JSON 바디로 전달된 Big5 결과를 저장"""
        db_big5 = Big5TestResult(**data.dict())
        self.db.add(db_big5)
        self.db.commit()
        self.db.refresh(db_big5)
        return db_big5
