from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.services.big5_test_service import Big5TestService
from app.schemas.big5_test import Big5TestResultResponse

router = APIRouter()

@router.post("/big5-tests/{user_id}", response_model=Big5TestResultResponse)
async def submit_big5_test(
    user_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """지원자 Big5 성격검사 제출 - 파일을 받아 지원자DB 저장 및 성격 유형별 점수 및 결과 해석 리턴"""
    service = Big5TestService(db)
    return service.submit_big5_test(user_id, file)

@router.get("/big5-tests/{user_id}", response_model=Big5TestResultResponse)
async def get_big5_test_result(
    user_id: str,
    db: Session = Depends(get_db)
):
    """지원자 Big5 성격검사 결과 조회"""
    service = Big5TestService(db)
    return service.get_big5_test_result(user_id)
