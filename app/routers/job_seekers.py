from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
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
    """구직자 마이페이지 - 기본 정보, 업로드 파일, Big5 성격검사 결과, AI QnA 가져오기"""
    service = JobSeekerService(db)
    return service.get_applicant_profile(user_id)

# 마이페이지 API - 모든 관련 데이터 포함
@router.get("/applicants/{user_id}", response_model=JobSeekerMyPageResponse)
async def get_applicant_mypage(
    user_id: str,
    db: Session = Depends(get_db)
):
    """구직자 마이페이지 - 기본 정보, Big5 성격검사 결과, AI 학습 응답, 문서 모두 포함"""
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
        'big5_test_results': mypage_data['big5_test_results'],
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

@router.post("/s3/upload/{user_id}/{document_type}")
async def upload_job_seeker_document_s3(
    user_id: str,
    document_type: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """구직자 문서 업로드 - S3 저장 (프론트엔드 호환)"""
    service = JobSeekerService(db)
    return await service.upload_file(user_id, document_type, file)

# 각 문서 타입별 개별 업로드 엔드포인트
@router.post("/s3/upload/{user_id}/cover_letter")
async def upload_cover_letter(
    user_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """자기소개서 업로드"""
    service = JobSeekerService(db)
    return await service.upload_file(user_id, "cover_letter", file)

@router.post("/s3/upload/{user_id}/resume")
async def upload_resume(
    user_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """이력서 업로드"""
    service = JobSeekerService(db)
    return await service.upload_file(user_id, "resume", file)

@router.post("/s3/upload/{user_id}/portfolio")
async def upload_portfolio(
    user_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """포트폴리오 업로드"""
    service = JobSeekerService(db)
    return await service.upload_file(user_id, "portfolio", file)

@router.post("/s3/upload/{user_id}/award")
async def upload_award(
    user_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """수상경력 업로드"""
    service = JobSeekerService(db)
    return await service.upload_file(user_id, "award", file)

@router.post("/s3/upload/{user_id}/certificate")
async def upload_certificate(
    user_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """증명서 업로드"""
    service = JobSeekerService(db)
    return await service.upload_file(user_id, "certificate", file)

@router.post("/s3/upload/{user_id}/qualification")
async def upload_qualification(
    user_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """자격증 업로드"""
    service = JobSeekerService(db)
    return await service.upload_file(user_id, "qualification", file)

@router.post("/s3/upload/{user_id}/paper")
async def upload_paper(
    user_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """논문 업로드"""
    service = JobSeekerService(db)
    return await service.upload_file(user_id, "paper", file)

@router.post("/s3/upload/{user_id}/other")
async def upload_other(
    user_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """기타자료 업로드"""
    service = JobSeekerService(db)
    return await service.upload_file(user_id, "other", file)

@router.post("/s3/upload/{user_id}/github")
async def upload_github(
    user_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """GitHub 링크 업로드"""
    service = JobSeekerService(db)
    return await service.upload_file(user_id, "github", file)

@router.get("/s3/files/{user_id}")
async def get_user_files(user_id: str, db: Session = Depends(get_db)):
    """사용자별 파일 목록 조회 (프론트엔드 호환)"""
    service = JobSeekerService(db)
    mypage_data = service.get_mypage_data(user_id)
    
    if not mypage_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="구직자 정보를 찾을 수 없습니다"
        )
    
    # 문서 목록을 타입별로 그룹화
    documents = mypage_data['documents']
    
    # 타입별로 그룹화
    grouped_files = {
        "award": [],
        "certificate": [],
        "cover_letter": [],
        "other": [],
        "paper": [],
        "portfolio": [],
        "qualification": [],
        "resume": [],
        "github": []
    }
    
    for doc in documents:
        doc_type = getattr(doc, 'document_type', 'other')
        if doc_type in grouped_files:
            grouped_files[doc_type].append({
                "name": getattr(doc, 'file_name', ''),
                "size": getattr(doc, 'file_size', 0),
                "lastModified": getattr(doc, 'created_at', ''),
                "downloadUrl": getattr(doc, 'file_url', '')
            })
    
    return grouped_files

@router.delete("/s3/delete/{user_id}/{file_type}/{file_name}")
async def delete_file(
    user_id: str,
    file_type: str,
    file_name: str,
    db: Session = Depends(get_db)
):
    """파일 삭제 API (프론트엔드 호환)"""
    service = JobSeekerService(db)
    return await service.delete_file(user_id, file_type, file_name)

# 각 문서 타입별 개별 삭제 엔드포인트
@router.delete("/s3/delete/{user_id}/cover_letter/{file_name}")
async def delete_cover_letter(
    user_id: str,
    file_name: str,
    db: Session = Depends(get_db)
):
    """자기소개서 삭제"""
    service = JobSeekerService(db)
    return await service.delete_file(user_id, "cover_letter", file_name)

@router.delete("/s3/delete/{user_id}/resume/{file_name}")
async def delete_resume(
    user_id: str,
    file_name: str,
    db: Session = Depends(get_db)
):
    """이력서 삭제"""
    service = JobSeekerService(db)
    return await service.delete_file(user_id, "resume", file_name)

@router.delete("/s3/delete/{user_id}/portfolio/{file_name}")
async def delete_portfolio(
    user_id: str,
    file_name: str,
    db: Session = Depends(get_db)
):
    """포트폴리오 삭제"""
    service = JobSeekerService(db)
    return await service.delete_file(user_id, "portfolio", file_name)

@router.delete("/s3/delete/{user_id}/award/{file_name}")
async def delete_award(
    user_id: str,
    file_name: str,
    db: Session = Depends(get_db)
):
    """수상경력 삭제"""
    service = JobSeekerService(db)
    return await service.delete_file(user_id, "award", file_name)

@router.delete("/s3/delete/{user_id}/certificate/{file_name}")
async def delete_certificate(
    user_id: str,
    file_name: str,
    db: Session = Depends(get_db)
):
    """증명서 삭제"""
    service = JobSeekerService(db)
    return await service.delete_file(user_id, "certificate", file_name)

@router.delete("/s3/delete/{user_id}/qualification/{file_name}")
async def delete_qualification(
    user_id: str,
    file_name: str,
    db: Session = Depends(get_db)
):
    """자격증 삭제"""
    service = JobSeekerService(db)
    return await service.delete_file(user_id, "qualification", file_name)

@router.delete("/s3/delete/{user_id}/paper/{file_name}")
async def delete_paper(
    user_id: str,
    file_name: str,
    db: Session = Depends(get_db)
):
    """논문 삭제"""
    service = JobSeekerService(db)
    return await service.delete_file(user_id, "paper", file_name)

@router.delete("/s3/delete/{user_id}/other/{file_name}")
async def delete_other(
    user_id: str,
    file_name: str,
    db: Session = Depends(get_db)
):
    """기타자료 삭제"""
    service = JobSeekerService(db)
    return await service.delete_file(user_id, "other", file_name)

@router.delete("/s3/delete/{user_id}/github/{file_name}")
async def delete_github(
    user_id: str,
    file_name: str,
    db: Session = Depends(get_db)
):
    """GitHub 링크 삭제"""
    service = JobSeekerService(db)
    return await service.delete_file(user_id, "github", file_name)

