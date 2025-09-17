from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.services.job_posting_service import JobPostingService
from app.core.security import verify_token
from app.services.auth_service import AuthService
from app.models.company import Company

router = APIRouter()

def get_current_company(
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    """토큰에서 회사 정보를 추출하여 반환"""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="인증 토큰이 필요합니다")
    token = authorization.split(" ", 1)[1].strip()
    email = verify_token(token)
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="유효하지 않은 토큰입니다")

    auth_service = AuthService(db)
    user = auth_service.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="사용자를 찾을 수 없습니다")

    company = db.query(Company).filter(Company.user_id == user.id).first()
    if not company:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="회사 계정이 아닙니다")
    return company

@router.get("/job-postings")
async def get_job_postings(
    db: Session = Depends(get_db),
    current_company: Company = Depends(get_current_company)
):
    """기업 채용관리 페이지 - 공고 리스트 가져오기"""
    service = JobPostingService(db)
    return service.get_job_postings(current_company.id)

@router.post("/job-postings")
async def create_job_posting(
    posting_data: dict,
    db: Session = Depends(get_db),
    current_company: Company = Depends(get_current_company)
):
    """기업 구인공고 생성"""
    service = JobPostingService(db)
    return service.create_job_posting(posting_data, current_company.id)

@router.get("/job-postings/{job_posting_id}")
async def get_job_posting(
    job_posting_id: str,
    db: Session = Depends(get_db)
):
    """기업 구인공고 공고보기"""
    service = JobPostingService(db)
    return service.get_job_posting(job_posting_id)

@router.put("/job-postings/{job_posting_id}")
async def close_job_posting(
    job_posting_id: str,
    db: Session = Depends(get_db)
):
    """기업 채용관리 공고마감"""
    service = JobPostingService(db)
    return service.close_job_posting(job_posting_id)
