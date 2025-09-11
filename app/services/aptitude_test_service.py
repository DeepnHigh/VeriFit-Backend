from sqlalchemy.orm import Session
from app.models.aptitude_test_result import AptitudeTestResult
from app.schemas.aptitude_test import AptitudeTestResultCreate
from typing import Optional
import uuid

class AptitudeTestService:
    def __init__(self, db: Session):
        self.db = db

    def submit_aptitude_test(self, user_id: str, file) -> AptitudeTestResult:
        """적성검사 파일을 받아 지원자DB 저장 및 유형별 점수 및 결과 해석 리턴"""
        # TODO: 파일 파싱 및 AI 분석 로직 구현
        # 임시로 더미 데이터 반환
        
        aptitude_data = AptitudeTestResultCreate(
            job_seeker_id=user_id,
            test_duration_minutes=30,
            realistic_score=75.5,
            investigative_score=82.3,
            artistic_score=68.7,
            social_score=79.1,
            enterprising_score=85.2,
            conventional_score=71.4,
            overall_analysis="현실형과 진취형 성향이 강한 지원자입니다."
        )
        
        db_aptitude = AptitudeTestResult(**aptitude_data.dict())
        self.db.add(db_aptitude)
        self.db.commit()
        self.db.refresh(db_aptitude)
        
        return db_aptitude

    def get_aptitude_test_result(self, user_id: str) -> Optional[AptitudeTestResult]:
        """지원자 적성검사 결과 조회"""
        return self.db.query(AptitudeTestResult).filter(
            AptitudeTestResult.job_seeker_id == user_id
        ).first()
