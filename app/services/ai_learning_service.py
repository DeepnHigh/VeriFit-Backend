from sqlalchemy.orm import Session
from app.models.ai_learning_question import AILearningQuestion
from app.models.job_seeker_ai_learning_response import JobSeekerAILearningResponse
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
        
        db_response = JobSeekerAILearningResponse(
            job_seeker_id=user_id,
            question_id=question_id,
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
        
        # 기존 응답 찾기 (가장 최근 것)
        existing_response = self.db.query(JobSeekerAILearningResponse).filter(
            JobSeekerAILearningResponse.job_seeker_id == user_id
        ).order_by(JobSeekerAILearningResponse.response_date.desc()).first()
        
        if existing_response:
            existing_response.answer_text = response_data.answer
            self.db.commit()
            self.db.refresh(existing_response)
            return existing_response
        else:
            # 새 응답 생성
            return self.create_ai_learning_response(user_id, "", response_data)

    def get_user_ai_learning_responses(self, user_id: str) -> List[JobSeekerAILearningResponse]:
        """지원자 AI 학습 질문답변 목록 조회"""
        return self.db.query(JobSeekerAILearningResponse).filter(
            JobSeekerAILearningResponse.job_seeker_id == user_id
        ).order_by(JobSeekerAILearningResponse.response_date.desc()).all()
