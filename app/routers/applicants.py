from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.services.applicant_service import ApplicantService

router = APIRouter()

@router.get("/applicants/{user_id}")
async def get_applicant_profile(
    user_id: int,
    db: Session = Depends(get_db)
):
    """지원자 마이페이지 - 기본 정보, 업로드 파일, 적성검사 결과, AI QnA 가져오기"""
    service = ApplicantService(db)
    return service.get_applicant_profile(user_id)

@router.post("/applicants/bio/{user_id}")
async def create_applicant_bio(
    user_id: int,
    bio: str,
    db: Session = Depends(get_db)
):
    """지원자 짧은소개 등록"""
    service = ApplicantService(db)
    return service.create_bio(user_id, bio)

@router.put("/applicants/bio/{user_id}")
async def update_applicant_bio(
    user_id: int,
    bio: str,
    db: Session = Depends(get_db)
):
    """지원자 짧은소개 수정"""
    service = ApplicantService(db)
    return service.update_bio(user_id, bio)

@router.post("/applicants/info/{user_id}")
async def create_applicant_info(
    user_id: int,
    info_data: dict,
    db: Session = Depends(get_db)
):
    """지원자 기본정보 직접 등록"""
    service = ApplicantService(db)
    return service.create_applicant_info(user_id, info_data)

@router.put("/applicants/info/{user_id}")
async def update_applicant_info(
    user_id: int,
    info_data: dict,
    db: Session = Depends(get_db)
):
    """지원자 기본정보 수정"""
    service = ApplicantService(db)
    return service.update_applicant_info(user_id, info_data)
