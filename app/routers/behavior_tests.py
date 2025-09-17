from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Body
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
