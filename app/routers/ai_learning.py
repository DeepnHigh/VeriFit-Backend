from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.services.ai_learning_service import AILearningService
from app.schemas.ai_learning import (
    AILearningQuestionResponse, 
    AILearningAnswerCreate, 
    AILearningAnswerResponse
)

router = APIRouter()

@router.get("/own-qnas/questions", response_model=list[AILearningQuestionResponse])
async def get_ai_learning_questions(
    db: Session = Depends(get_db)
):
    """AI 학습용 질문 목록 조회"""
    service = AILearningService(db)
    return service.get_ai_learning_questions()

@router.post("/own-qnas/{user_id}/{question_id}", response_model=AILearningAnswerResponse)
async def create_ai_learning_answer(
    user_id: str,
    question_id: str,
    response_data: AILearningAnswerCreate,
    db: Session = Depends(get_db)
):
    """지원자 질문답변 생성 - AI학습을 위한 질문답변 작성"""
    service = AILearningService(db)
    return service.create_ai_learning_answer(user_id, question_id, response_data)

@router.put("/own-qnas/{user_id}", response_model=AILearningAnswerResponse)
async def update_ai_learning_answer(
    user_id: str,
    response_data: AILearningAnswerCreate,
    db: Session = Depends(get_db)
):
    """지원자 질문답변 수정 - AI학습을 위한 질문답변 수정"""
    service = AILearningService(db)
    return service.update_ai_learning_answer(user_id, response_data)

@router.get("/own-qnas/{user_id}", response_model=list[AILearningAnswerResponse])
async def get_user_ai_learning_answers(
    user_id: str,
    db: Session = Depends(get_db)
):
    """지원자 AI 학습 질문답변 목록 조회"""
    service = AILearningService(db)
    return service.get_user_ai_learning_answers(user_id)
