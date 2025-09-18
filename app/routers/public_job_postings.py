from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.services.job_posting_service import JobPostingService
from app.schemas.job_posting import PublicJobPostingsResponse, PublicJobPostingsErrorResponse

router = APIRouter()

@router.get("/public/job-postings", 
           response_model=PublicJobPostingsResponse,
           responses={
               500: {"model": PublicJobPostingsErrorResponse}
           })
async def get_public_job_postings(
    include_closed: bool = Query(False, description="마감된 공고 포함 여부"),
    db: Session = Depends(get_db)
):
    """
    공개 채용공고 조회 API
    
    - **include_closed**: 마감된 공고 포함 여부 (기본값: false)
      - false: is_active=true이고 application_deadline이 현재 날짜 이후인 공고만 반환
      - true: 모든 공고 반환 (마감된 공고 포함)
    
    인증 토큰이 필요하지 않은 공개 API입니다.
    """
    service = JobPostingService(db)
    result = service.get_public_job_postings(include_closed)
    
    if not result["success"]:
        raise HTTPException(
            status_code=500,
            detail=result["message"]
        )
    
    return result
