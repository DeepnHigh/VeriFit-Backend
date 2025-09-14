from sqlalchemy.orm import Session
from app.models.big5_test_result import Big5TestResult
from app.schemas.big5_test import Big5TestResultCreate
from typing import Optional
import uuid

class Big5TestService:
    def __init__(self, db: Session):
        self.db = db

    def submit_big5_test(self, user_id: str, file) -> Big5TestResult:
        """Big5 성격검사 파일을 받아 지원자DB 저장 및 성격 유형별 점수 및 결과 해석 리턴"""
        # TODO: 파일 파싱 및 AI 분석 로직 구현
        # 임시로 더미 데이터 반환
        
        big5_data = Big5TestResultCreate(
            job_seeker_id=user_id,
            openness_score=75.5,
            conscientiousness_score=82.3,
            extraversion_score=68.7,
            agreeableness_score=79.1,
            neuroticism_score=45.2,
            openness_level="high",
            conscientiousness_level="high",
            extraversion_level="neutral",
            agreeableness_level="high",
            neuroticism_level="low",
            openness_facets={
                "imagination": 78.0,
                "artistic_interests": 72.0,
                "emotionality": 65.0,
                "adventurousness": 80.0,
                "intellect": 85.0,
                "liberalism": 70.0
            },
            conscientiousness_facets={
                "self_efficacy": 85.0,
                "orderliness": 80.0,
                "dutifulness": 90.0,
                "achievement_striving": 88.0,
                "self_discipline": 75.0,
                "cautiousness": 70.0
            },
            extraversion_facets={
                "friendliness": 75.0,
                "gregariousness": 65.0,
                "assertiveness": 70.0,
                "activity_level": 80.0,
                "excitement_seeking": 60.0,
                "cheerfulness": 75.0
            },
            agreeableness_facets={
                "trust": 85.0,
                "morality": 90.0,
                "altruism": 88.0,
                "cooperation": 82.0,
                "modesty": 70.0,
                "sympathy": 85.0
            },
            neuroticism_facets={
                "anxiety": 30.0,
                "anger": 25.0,
                "depression": 20.0,
                "self_consciousness": 40.0,
                "immoderation": 35.0,
                "vulnerability": 30.0
            },
            interpretations={
                "korean": "개방성과 성실성이 높고, 신경성이 낮은 안정적인 성격을 보입니다. 창의적이고 체계적인 접근을 선호하며, 스트레스에 잘 대처하는 능력이 뛰어납니다.",
                "english": "Shows high openness and conscientiousness with low neuroticism, indicating a stable personality. Prefers creative and systematic approaches with excellent stress management abilities."
            },
            raw_scores={
                "total_questions": 120,
                "completion_time_minutes": 25,
                "response_consistency": 0.92
            }
        )
        
        db_big5 = Big5TestResult(**big5_data.dict())
        self.db.add(db_big5)
        self.db.commit()
        self.db.refresh(db_big5)
        
        return db_big5

    def get_big5_test_result(self, user_id: str) -> Optional[Big5TestResult]:
        """지원자 Big5 성격검사 결과 조회"""
        return self.db.query(Big5TestResult).filter(
            Big5TestResult.job_seeker_id == user_id
        ).first()
