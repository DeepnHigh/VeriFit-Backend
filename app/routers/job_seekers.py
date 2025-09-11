from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.services.job_seeker_service import JobSeekerService
from app.schemas.job_seeker import (
    JobSeekerResponse, JobSeekerUpdate, JobSeekerDocumentResponse
)

router = APIRouter()

@router.get("/job-seekers/{user_id}", response_model=JobSeekerResponse)
async def get_job_seeker_profile(
    user_id: str,
    db: Session = Depends(get_db)
):
    """구직자 마이페이지 - 기본 정보, 업로드 파일, 적성검사 결과, AI QnA 가져오기"""
    service = JobSeekerService(db)
    return service.get_applicant_profile(user_id)

# 별칭 라우트: /applicants/{user_id} -> 동일 핸들러
@router.get("/applicants/{user_id}", response_model=JobSeekerResponse)
async def get_applicant_profile(
    user_id: str,
    db: Session = Depends(get_db)
):
    service = JobSeekerService(db)
    return service.get_applicant_profile(user_id)

@router.post("/applicants/bio/{user_id}", response_model=JobSeekerResponse)
async def create_job_seeker_bio(
    user_id: str,
    bio: str,
    db: Session = Depends(get_db)
):
    """구직자 짧은소개 등록"""
    service = JobSeekerService(db)
    return service.create_bio(user_id, bio)

@router.put("/applicants/bio/{user_id}", response_model=JobSeekerResponse)
async def update_job_seeker_bio(
    user_id: str,
    bio: str,
    db: Session = Depends(get_db)
):
    """구직자 짧은소개 수정"""
    service = JobSeekerService(db)
    return service.update_bio(user_id, bio)

@router.post("/applicants/info/{user_id}", response_model=JobSeekerResponse)
async def create_job_seeker_info(
    user_id: str,
    info_data: JobSeekerUpdate,
    db: Session = Depends(get_db)
):
    """구직자 기본정보 직접 등록"""
    service = JobSeekerService(db)
    return service.create_applicant_info(user_id, info_data.model_dump(exclude_unset=True))

@router.put("/applicants/info/{user_id}", response_model=JobSeekerResponse)
async def update_job_seeker_info(
    user_id: str,
    info_data: JobSeekerUpdate,
    db: Session = Depends(get_db)
):
    """구직자 기본정보 수정"""
    service = JobSeekerService(db)
    return service.update_applicant_info(user_id, info_data.model_dump(exclude_unset=True))

