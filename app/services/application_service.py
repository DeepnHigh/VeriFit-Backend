from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime

from app.models.application import Application
from app.models.job_posting import JobPosting
from app.models.job_seeker import JobSeeker

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
