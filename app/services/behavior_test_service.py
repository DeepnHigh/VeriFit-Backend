from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import uuid
from app.models.job_seeker import JobSeeker

class BehaviorTestService:
    def __init__(self, db: Session):
        self.db = db

    def save_behavior_text(self, user_id: str, behavior_text: str) -> Dict[str, Any]:
        """behavior_text를 job_seekers.behavior_text에 저장"""
        try:
            uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        except Exception:
            return {"success": False, "message": "잘못된 user_id 형식"}

        job_seeker = self.db.query(JobSeeker).filter(JobSeeker.user_id == uid).first()
        if not job_seeker:
            return {"success": False, "message": "구직자 정보를 찾을 수 없습니다"}

        try:
            job_seeker.behavior_text = behavior_text or ""
            self.db.add(job_seeker)
            self.db.commit()
            return {"success": True, "message": "저장되었습니다"}
        except Exception as e:
            self.db.rollback()
            return {"success": False, "message": f"저장 실패: {str(e)}"}

    def get_behavior_text(self, user_id: str) -> Dict[str, Any]:
        """지원자 behavior_text 조회"""
        try:
            uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        except Exception:
            return {"success": False, "message": "잘못된 user_id 형식"}

        job_seeker = self.db.query(JobSeeker).filter(JobSeeker.user_id == uid).first()
        if not job_seeker:
            return {"success": False, "message": "구직자 정보를 찾을 수 없습니다"}

        return {"success": True, "behavior_text": job_seeker.behavior_text or ""}
