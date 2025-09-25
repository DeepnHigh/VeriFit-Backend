from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime

from app.models.application import Application
from app.models.job_posting import JobPosting
from app.models.job_seeker import JobSeeker
from app.models.ai_overall_report import AIOverallReport

class ApplicationService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_application(self, job_posting_id: str, job_seeker_id: str) -> Dict[str, Any]:
        # 필수값 검증
        if not job_posting_id or not job_seeker_id:
            return {"status": 400, "success": False, "message": "필수값 누락"}
        
        # 공고 존재 확인
        posting = self.db.query(JobPosting).filter(JobPosting.id == job_posting_id).first()
        if not posting:
            return {"status": 404, "success": False, "message": "존재하지 않는 채용공고입니다"}
        
        # 구직자 존재 확인
        seeker = self.db.query(JobSeeker).filter(JobSeeker.id == job_seeker_id).first()
        if not seeker:
            return {"status": 404, "success": False, "message": "존재하지 않는 지원자입니다"}
        
        # 중복 지원 확인
        exists = (
            self.db.query(Application)
            .filter(and_(
                Application.job_posting_id == job_posting_id,
                Application.job_seeker_id == job_seeker_id
            ))
            .first()
        )
        if exists:
            return {"status": 409, "success": False, "message": "이미 지원한 공고입니다"}
        
        # 생성
        application = Application(
            job_posting_id=job_posting_id,
            job_seeker_id=job_seeker_id,
            application_status='submitted'
        )
        self.db.add(application)
        self.db.commit()
        self.db.refresh(application)
        
        # AI 전체 리포트: 총 지원자 수 증가 (리포트가 존재할 때만)
        try:
            report = (
                self.db.query(AIOverallReport)
                .filter(AIOverallReport.job_posting_id == job_posting_id)
                .first()
            )
            if report:
                report.total_applications = (report.total_applications or 0) + 1
                self.db.commit()
        except Exception:
            # 리포트 업데이트 실패는 지원 생성 성공을 막지 않음
            self.db.rollback()

        return {
            "status": 200,
            "success": True,
            "data": {
                "id": str(application.id),
                "job_posting_id": str(application.job_posting_id),
                "job_seeker_id": str(application.job_seeker_id),
                "application_status": application.application_status,
                "applied_at": application.applied_at.isoformat() if application.applied_at else datetime.utcnow().isoformat() + "Z"
            }
        }

    def list_applications_by_job_seeker(self, job_seeker_id: str) -> Dict[str, Any]:
        """
        지원자의 지원 목록을 조회합니다.
        - job_seeker_id가 실제 job_seekers.id가 아닐 경우 user_id로 매핑 시도
        - 결과는 프론트 요구 스키마에 맞춰 배열로 반환
        """
        # 1) 입력값을 UUID로 파싱 시도
        from uuid import UUID
        seeker = None
        try:
            parsed = UUID(job_seeker_id)
            seeker = self.db.query(JobSeeker).filter(JobSeeker.id == parsed).first()
        except Exception:
            seeker = None

        # 2) seeker가 없으면 user_id로 매핑 시도
        if not seeker:
            try:
                parsed_user = UUID(job_seeker_id)
                seeker = self.db.query(JobSeeker).filter(JobSeeker.user_id == parsed_user).first()
            except Exception:
                seeker = None

        if not seeker:
            return {"status": 404, "success": False, "message": "지원자를 찾을 수 없습니다."}

        # 3) applications 조인 조회
        from sqlalchemy.orm import joinedload
        query = (
            self.db.query(Application)
            .options(
                joinedload(Application.job_posting).joinedload(JobPosting.company)
            )
            .filter(Application.job_seeker_id == seeker.id)
            .order_by(Application.applied_at.desc())
        )

        rows: List[Application] = query.all()
        items: List[Dict[str, Any]] = []
        for app in rows:
            job_posting = app.job_posting
            company_name = job_posting.company.company_name if (job_posting and job_posting.company) else None
            items.append({
                "applications_id": str(app.id),
                "job_posting_id": str(job_posting.id) if job_posting else None,
                "job_title": job_posting.title if job_posting else None,
                "company_name": company_name,
                "applied_at": app.applied_at.isoformat() if app.applied_at else None,
                "status": app.application_status
            })

        return {"status": 200, "success": True, "data": items}
