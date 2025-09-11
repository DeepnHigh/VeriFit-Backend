from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.services.aptitude_test_service import AptitudeTestService
from app.schemas.aptitude_test import AptitudeTestResultResponse

router = APIRouter()

@router.post("/aptitudes/{user_id}", response_model=AptitudeTestResultResponse)
async def submit_aptitude_test(
    user_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """지원자 적성검사 제출 - 파일을 받아 지원자DB 저장 및 유형별 점수 및 결과 해석 리턴"""
    service = AptitudeTestService(db)
    return service.submit_aptitude_test(user_id, file)

@router.get("/aptitudes/{user_id}", response_model=AptitudeTestResultResponse)
async def get_aptitude_test_result(
    user_id: str,
    db: Session = Depends(get_db)
):
    """지원자 적성검사 결과 조회"""
    service = AptitudeTestService(db)
    return service.get_aptitude_test_result(user_id)
