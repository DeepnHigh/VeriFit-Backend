from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.services.interview_service import InterviewService
from app.schemas.interview import RecruitmentStatusResponse

router = APIRouter()

@router.post("/interviews/{job_posting_id}")
async def create_interview_and_report(
    job_posting_id: str,
    db: Session = Depends(get_db)
):
    """질의응답 및 리포트 생성 - 지원자AI와 면접관AI 인터뷰 진행"""
    service = InterviewService(db)
    return service.create_interview_and_report(job_posting_id)

@router.post("/interviews/{job_posting_id}/start-evaluation")
async def start_evaluation(
    job_posting_id: str,
    db: Session = Depends(get_db)
):
    """
    AI 평가 시작 - job_posting의 eval_status를 'ing'로 업데이트
    
    TODO: 
    1. AI 대결 시스템 구현 (기업 AI vs 지원자 AI)
    2. RAG 기반 채용공고 정보 생성
    3. RAG 기반 지원자 이력서 정보 생성
    4. AWS Bedrock Lambda를 통한 AI 평가 실행
    5. 평가 결과를 AIEvaluation 테이블에 저장
    6. eval_status를 'finish'로 업데이트
    """
    service = InterviewService(db)
    result = service.start_evaluation(job_posting_id)
    
    if not result.get("success"):
        status_code = result.get("status", 500)
        raise HTTPException(status_code=status_code, detail=result.get("message", "AI 평가 시작에 실패했습니다"))
    
    return result

@router.get("/interviews/{job_posting_id}", response_model=RecruitmentStatusResponse)
async def get_recruitment_status(
    job_posting_id: str,
    db: Session = Depends(get_db)
):
    """기업 채용현황 페이지 - overall_report, 지원자 순위 가져오기"""
    service = InterviewService(db)
    return service.get_recruitment_status(job_posting_id)

@router.get("/interviews/detail/{application_id}")
async def get_individual_report(
    application_id: str,
    db: Session = Depends(get_db)
):
    """개별리포트 조회 - AI 평가, 적성검사, 행동검사, 면접 하이라이트"""
    service = InterviewService(db)
    return service.get_individual_report(application_id)

@router.get("/interviews/report/{application_id}")
async def get_individual_report_by_application(
    application_id: str,
    db: Session = Depends(get_db)
):
    """기업 리포트 조회 - applications_id로 지원자 이름 반환 (임시 간소 응답)"""
    service = InterviewService(db)
    result = service.get_individual_report_by_application(application_id)
    if not result.get("success"):
        status_code = result.get("status", 404)
        raise HTTPException(status_code=status_code, detail=result.get("message", "리포트를 찾을 수 없습니다"))
    return result

@router.get("/company/interviews/report/{application_id}")
async def get_company_individual_report_by_application(
    application_id: str,
    db: Session = Depends(get_db)
):
    """기업 리포트 조회 (company prefix) - applications_id로 지원자 이름 반환 (임시)"""
    service = InterviewService(db)
    result = service.get_individual_report_by_application(application_id)
    if not result.get("success"):
        status_code = result.get("status", 404)
        raise HTTPException(status_code=status_code, detail=result.get("message", "리포트를 찾을 수 없습니다"))
    return result

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

@router.get("/company/interviews/profiles/{application_id}")
async def get_company_applicant_profile(
    application_id: str,
    db: Session = Depends(get_db)
):
    """기업용 지원자 프로필 조회 (company prefix) - applications_id로 지원자 정보 반환"""
    service = InterviewService(db)
    result = service.get_applicant_profile_by_application(application_id)
    if not result.get("success"):
        status_code = result.get("status", 404)
        raise HTTPException(status_code=status_code, detail=result.get("message", "지원자 프로필을 찾을 수 없습니다"))
    return result
