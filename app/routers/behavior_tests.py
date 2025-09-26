from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Body, Form
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.services.behavior_test_service import BehaviorTestService

router = APIRouter()

@router.post("/behavior/save/{user_id}")
async def save_behavior_text(
    user_id: str,
    payload: dict = Body(...),
    db: Session = Depends(get_db)
):
    """behavior_text를 job_seekers.behavior_text에 저장"""
    behavior_text = payload.get("behavior_text", "")
    service = BehaviorTestService(db)
    return service.save_behavior_text(user_id, behavior_text)

@router.get("/behavior/{user_id}")
async def get_behavior_text(
    user_id: str,
    db: Session = Depends(get_db)
):
    """behavior_text 조회"""
    service = BehaviorTestService(db)
    return service.get_behavior_text(user_id)

@router.post("/behaviors/{user_id}")
async def create_behavior_test_result(
    user_id: str,
    situation_text: str = Form(...),
    selected_character: str = Form(...),
    conversation_history: str = Form(...),
    db: Session = Depends(get_db)
):
    """행동검사 결과 저장 (multipart/form-data)

    필드:
    - situation_text: 시나리오 전체 텍스트
    - selected_character: 'A' | 'B' | 'C'
    - conversation_history: JSON 문자열 (메시지 배열)
    """
    service = BehaviorTestService(db)
    return service.save_behavior_result(user_id, situation_text, selected_character, conversation_history)
