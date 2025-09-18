from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.services.interview_service import InterviewService

router = APIRouter()

@router.post("/interviews/{job_posting_id}")
async def create_interview_and_report(
    job_posting_id: str,
    db: Session = Depends(get_db)
):
    """질의응답 및 리포트 생성 - 지원자AI와 면접관AI 인터뷰 진행"""
    service = InterviewService(db)
    return service.create_interview_and_report(job_posting_id)

@router.get("/interviews/{job_posting_id}")
async def get_recruitment_status(
    job_posting_id: str,
    db: Session = Depends(get_db)
):
    """기업 채용현황 페이지 - overall_report, 지원자 순위 가져오기"""
    service = InterviewService(db)
    return service.get_recruitment_status(job_posting_id)

@router.get("/interviews/{application_id}")
async def get_individual_report(
    application_id: str,
    db: Session = Depends(get_db)
):
    """개별리포트 조회 - AI 평가, 적성검사, 행동검사, 면접 하이라이트"""
    service = InterviewService(db)
    return service.get_individual_report(application_id)

@router.get("/interviews/conversations/{application_id}")
async def get_interview_conversations(
    application_id: int,
    db: Session = Depends(get_db)
):
    """AI 면접 대화 전체 조회"""
    service = InterviewService(db)
    return service.get_interview_conversations(application_id)

@router.get("/interviews/profiles/{application_id}")
async def get_applicant_profile_for_company(
    application_id: int,
    db: Session = Depends(get_db)
):
    """지원자 프로필 조회 (기업전용)"""
    service = InterviewService(db)
    return service.get_applicant_profile_for_company(application_id)
