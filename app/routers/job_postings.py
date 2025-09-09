from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.services.job_posting_service import JobPostingService

router = APIRouter()

@router.get("/job-postings")
async def get_job_postings(
    db: Session = Depends(get_db)
):
    """기업 채용관리 페이지 - 공고 리스트 가져오기"""
    service = JobPostingService(db)
    return service.get_job_postings()

@router.post("/job-postings")
async def create_job_posting(
    posting_data: dict,
    db: Session = Depends(get_db)
):
    """기업 구인공고 생성"""
    service = JobPostingService(db)
    return service.create_job_posting(posting_data)

@router.get("/job-postings/{job_posting_id}")
async def get_job_posting(
    job_posting_id: int,
    db: Session = Depends(get_db)
):
    """기업 구인공고 공고보기"""
    service = JobPostingService(db)
    return service.get_job_posting(job_posting_id)

@router.put("/job-postings/{job_posting_id}")
async def close_job_posting(
    job_posting_id: int,
    db: Session = Depends(get_db)
):
    """기업 채용관리 공고마감"""
    service = JobPostingService(db)
    return service.close_job_posting(job_posting_id)
