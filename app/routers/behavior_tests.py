from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.services.behavior_test_service import BehaviorTestService

router = APIRouter()

@router.post("/behaviors/{user_id}")
async def submit_behavior_test(
    user_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """지원자 행동검사 제출 - 파일을 받아 지원자DB 저장"""
    service = BehaviorTestService(db)
    return service.submit_behavior_test(user_id, file)

@router.get("/behaviors/{user_id}")
async def get_behavior_test_result(
    user_id: str,
    db: Session = Depends(get_db)
):
    """지원자 행동검사 결과 조회"""
    service = BehaviorTestService(db)
    return service.get_behavior_test_result(user_id)
