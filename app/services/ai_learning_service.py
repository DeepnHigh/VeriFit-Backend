from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import uuid
from app.models.ai_learning_question import AILearningQuestion
from app.models.job_seeker_ai_learning_response import JobSeekerAILearningResponse
from app.models.job_seeker import JobSeeker
from app.schemas.ai_learning import (
    AILearningQuestionCreate, 
    AILearningQuestionResponse,
    JobSeekerAILearningResponseCreate
)
from typing import List, Optional
import uuid

class AILearningService:
    def __init__(self, db: Session):
        self.db = db

    def _resolve_job_seeker_id(self, user_id: str) -> uuid.UUID:
        """주어진 사용자 ID(users.id)로 구직자 ID(job_seekers.id)를 조회한다."""
        # user_id는 users.id(UUID)를 문자열로 받을 수 있으므로 비교용으로 uuid 변환 시도
        try:
            user_uuid = uuid.UUID(user_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid user_id UUID format")

        job_seeker = self.db.query(JobSeeker).filter(JobSeeker.user_id == user_uuid).first()
        if job_seeker is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job seeker not found for given user_id")
        return job_seeker.id

    def get_ai_learning_questions(self) -> List[AILearningQuestionResponse]:
        """AI 학습용 질문 목록 조회"""
        questions = self.db.query(AILearningQuestion).order_by(
            AILearningQuestion.display_order
        ).all()
        
        # SQLAlchemy 모델을 Pydantic 모델로 변환
        return [
            AILearningQuestionResponse(
                id=str(question.id),
                question_text=question.question_text,
                display_order=question.display_order
            )
            for question in questions
        ]

    def create_ai_learning_response(
        self, 
        user_id: str, 
        question_id: str, 
        response_data: JobSeekerAILearningResponseCreate
    ) -> JobSeekerAILearningResponse:
        """지원자 질문답변 생성"""
        job_seeker_id = self._resolve_job_seeker_id(user_id)
        try:
            question_uuid = uuid.UUID(question_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid question_id UUID format")

        db_response = JobSeekerAILearningResponse(
            job_seeker_id=job_seeker_id,
            question_id=question_uuid,
            answer_text=response_data.answer
        )
        
        self.db.add(db_response)
        self.db.commit()
        self.db.refresh(db_response)
        
        return db_response

    def update_ai_learning_response(
        self, 
        user_id: str, 
        response_data: JobSeekerAILearningResponseCreate
    ) -> JobSeekerAILearningResponse:
        """지원자 질문답변 수정"""
        job_seeker_id = self._resolve_job_seeker_id(user_id)

        # 기존 응답 찾기 (가장 최근 것)
        existing_response = self.db.query(JobSeekerAILearningResponse).filter(
            JobSeekerAILearningResponse.job_seeker_id == job_seeker_id
        ).order_by(JobSeekerAILearningResponse.response_date.desc()).first()

        if existing_response is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No existing response to update")

        existing_response.answer_text = response_data.answer
        self.db.commit()
        self.db.refresh(existing_response)
        return existing_response

    def get_user_ai_learning_responses(self, user_id: str) -> List[JobSeekerAILearningResponse]:
        """지원자 AI 학습 질문답변 목록 조회"""
        job_seeker_id = self._resolve_job_seeker_id(user_id)
        return self.db.query(JobSeekerAILearningResponse).filter(
            JobSeekerAILearningResponse.job_seeker_id == job_seeker_id
        ).order_by(JobSeekerAILearningResponse.response_date.desc()).all()
