from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.services.big5_test_service import Big5TestService
from app.schemas.big5_test import Big5TestResultResponse, Big5TestResultCreate, Big5TestResultUpdate
from app.models.job_seeker import JobSeeker

router = APIRouter()


# 프런트 요청 규약에 맞춘 경로 매핑
@router.post("/big5-test", response_model=Big5TestResultResponse)
async def create_big5_test_result(
    payload: Big5TestResultCreate,
    db: Session = Depends(get_db)
):
    """Big5 검사 결과 저장 (JSON)"""
    # 프론트에서 job_seeker_id 자리에 userId가 전달되는 경우를 보정
    # 1) 우선 전달값이 실제 job_seekers.id 인지 확인
    js = db.query(JobSeeker).filter(JobSeeker.id == payload.job_seeker_id).first()
    if not js:
        # 2) 아니라면 user_id로 간주하고 매핑 시도
        js = db.query(JobSeeker).filter(JobSeeker.user_id == payload.job_seeker_id).first()
        if js:
            payload.job_seeker_id = str(js.id)
        else:
            # 매핑 실패 시 400 반환 (FK 위반 방지)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="job_seeker_id가 유효한 job_seeker의 id가 아니며 user_id로도 매핑되지 않습니다."
            )
    service = Big5TestService(db)
    return service.save_big5_result(payload)


@router.get("/big5-test/{job_seeker_id}", response_model=Big5TestResultResponse)
async def get_big5_test_result(
    job_seeker_id: str,
    db: Session = Depends(get_db)
):
    """지원자 Big5 성격검사 결과 조회"""
    # 프론트에서 job_seeker_id 자리에 userId가 전달되는 경우를 보정
    # 우선 입력이 실제 job_seeker의 id인지 확인하고, 아니면 user_id로 변환
    js = db.query(JobSeeker).filter(JobSeeker.id == job_seeker_id).first()
    if not js:
        js = db.query(JobSeeker).filter(JobSeeker.user_id == job_seeker_id).first()
        if js:
            job_seeker_id = str(js.id)
    service = Big5TestService(db)
    return service.get_big5_test_result(job_seeker_id)

@router.put("/big5-test/{id}", response_model=Big5TestResultResponse)
async def update_big5_test_result(
    id: str,
    payload: Big5TestResultUpdate,
    db: Session = Depends(get_db)
):
    """Big5 검사 결과 부분 업데이트"""
    service = Big5TestService(db)
    updated = service.update_big5_result(id, payload)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Big5 result not found")
    return updated


@router.delete("/big5-test/{id}")
async def delete_big5_test_result(
    id: str,
    db: Session = Depends(get_db)
):
    """Big5 검사 결과 삭제"""
    service = Big5TestService(db)
    ok = service.delete_big5_result(id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Big5 result not found")
    return {"success": True}
