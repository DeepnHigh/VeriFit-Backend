from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.services.job_seeker_service import JobSeekerService
from app.schemas.job_seeker import (
    JobSeekerResponse, JobSeekerUpdate, JobSeekerDocumentResponse, JobSeekerMyPageResponse
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

# 마이페이지 API - 모든 관련 데이터 포함
@router.get("/applicants/{user_id}", response_model=JobSeekerMyPageResponse)
async def get_applicant_mypage(
    user_id: str,
    db: Session = Depends(get_db)
):
    """구직자 마이페이지 - 기본 정보, 적성검사 결과, AI 학습 응답, 문서 모두 포함"""
    service = JobSeekerService(db)
    mypage_data = service.get_mypage_data(user_id)
    
    if not mypage_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="구직자 정보를 찾을 수 없습니다"
        )
    
    # JobSeeker 객체를 기본으로 하고 추가 데이터를 병합
    job_seeker = mypage_data['job_seeker']
    
    # Pydantic 모델에 맞게 데이터 구성
    response_data = {
        # JobSeeker 기본 정보
        'id': job_seeker.id,
        'user_id': job_seeker.user_id,
        'full_name': job_seeker.full_name,
        'phone': job_seeker.phone,
        'email': job_seeker.email,
        'profile_picture': job_seeker.profile_picture,
        'bio': job_seeker.bio,
        'total_experience_years': job_seeker.total_experience_years,
        'company_name': job_seeker.company_name,
        'education_level': job_seeker.education_level,
        'university': job_seeker.university,
        'major': job_seeker.major,
        'graduation_year': job_seeker.graduation_year,
        'github_repositories': job_seeker.github_repositories,
        'portfolios': job_seeker.portfolios,
        'resumes': job_seeker.resumes,
        'awards': job_seeker.awards,
        'certificates': job_seeker.certificates,
        'qualifications': job_seeker.qualifications,
        'papers': job_seeker.papers,
        'cover_letters': job_seeker.cover_letters,
        'other_documents': job_seeker.other_documents,
        'location': job_seeker.location,
        'profile_completion_percentage': job_seeker.profile_completion_percentage,
        'last_profile_update': job_seeker.last_profile_update,
        'is_profile_public': job_seeker.is_profile_public,
        'created_at': job_seeker.created_at,
        
        # 추가 관련 데이터
        'aptitude_test_results': mypage_data['aptitude_test_results'],
        'ai_learning_responses': mypage_data['ai_learning_responses'],
        'documents': mypage_data['documents']
    }
    
    return JobSeekerMyPageResponse(**response_data)

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

