from sqlalchemy.orm import Session
from sqlalchemy import func
from decimal import Decimal

from app.models.job_posting import JobPosting
from app.models.application import Application
from app.models.job_seeker import JobSeeker
from app.models.ai_evaluation import AIEvaluation
from app.models.ai_overall_report import AIOverallReport

class InterviewService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_interview_and_report(self, job_posting_id: int):
        """면접 및 리포트 생성"""
        # TODO: AI 면접 로직 구현
        return {
            "message": "면접이 진행되었습니다",
            "job_posting_id": job_posting_id,
            "interview_id": 1
        }
    
    def get_recruitment_status(self, job_posting_id: str):
        """채용현황 조회 (공고 정보, 지원 목록, 카운트)"""
        # 공고 존재 확인
        posting = (
            self.db.query(JobPosting)
            .filter(JobPosting.id == job_posting_id)
            .first()
        )
        if not posting:
            return {"status": 404, "success": False, "message": "채용공고를 찾을 수 없습니다"}

        # 지원 목록 조인 조회
        rows = (
            self.db.query(
                Application.id.label("application_id"),
                JobSeeker.user_id.label("user_id"),
                JobSeeker.full_name.label("candidate_name"),
                Application.applied_at.label("applied_at"),
                Application.application_status.label("stage"),
                AIEvaluation.total_score.label("overall_score"),
                AIEvaluation.hard_score.label("hard_score"),
                AIEvaluation.soft_score.label("soft_score"),
                AIEvaluation.ai_summary.label("ai_summary"),
            )
            .join(JobSeeker, JobSeeker.id == Application.job_seeker_id)
            .outerjoin(AIEvaluation, AIEvaluation.application_id == Application.id)
            .filter(Application.job_posting_id == job_posting_id)
            .order_by(Application.applied_at.desc())
            .all()
        )

        applications = []
        for r in rows:
            overall_score_val = None
            if r.overall_score is not None:
                # Decimal -> int
                try:
                    overall_score_val = int(Decimal(r.overall_score))
                except Exception:
                    overall_score_val = float(r.overall_score)
            hard_score_val = None
            if r.hard_score is not None:
                try:
                    hard_score_val = float(r.hard_score)
                except Exception:
                    hard_score_val = None
            soft_score_val = None
            if r.soft_score is not None:
                try:
                    soft_score_val = float(r.soft_score)
                except Exception:
                    soft_score_val = None
            applications.append({
                "applications_id": str(r.application_id),
                "user_id": str(r.user_id) if r.user_id else None,
                "candidate_name": r.candidate_name,
                "applied_at": r.applied_at.isoformat() if r.applied_at else None,
                "stage": r.stage,
                "overall_score": overall_score_val,
                "hard_score": hard_score_val,
                "soft_score": soft_score_val,
                "ai_summary": r.ai_summary,
            })

        # 카운트 집계
        total = len(applications)
        interviewed = sum(1 for a in applications if a.get("stage") in ("interviewed", "ai_evaluated"))
        offered = sum(1 for a in applications if a.get("stage") == "offered")
        rejected = sum(1 for a in applications if a.get("stage") == "rejected")

        # 공고별 AI 전체 리포트 조회
        report = (
            self.db.query(AIOverallReport)
            .filter(AIOverallReport.job_posting_id == job_posting_id)
            .first()
        )
        ai_overall_report = None
        if report:
            ai_overall_report = {
                "total_applications": report.total_applications,
                "ai_evaluated_count": report.ai_evaluated_count,
                "ai_recommended_count": report.ai_recommended_count,
                "overall_review": report.overall_review or "",
                "created_at": report.created_at.isoformat() if report.created_at else None,
            }
        else:
            ai_overall_report = {
                "total_applications": total,
                "ai_evaluated_count": interviewed,
                "ai_recommended_count": 0,
                "overall_review": "",
                "created_at": None,
            }

        return {
            "status": 200,
            "success": True,
            "data": {
                "job_posting": {
                    "id": str(posting.id),
                    "title": posting.title,
                    "status": "active" if posting.is_active else "inactive",
                    "created_at": posting.created_at.isoformat() if posting.created_at else None,
                    "hard_skills": posting.hard_skills or [],
                    "soft_skills": posting.soft_skills or [],
                },
                "applications": applications,
                "ai_overall_report": ai_overall_report,
                "counts": {
                    "total": total,
                    "interviewed": interviewed,
                    "offered": offered,
                    "rejected": rejected,
                },
            },
        }
    
    def get_individual_report(self, application_id: int):
        """개별 리포트 조회"""
        # TODO: 실제 데이터 조회 로직 구현
        return {
            "application_id": application_id,
            "ai_evaluations": {},
            "big5_test_results": {},
            "behavior_test_results": {},
            "interview_highlights": []
        }
    
    def get_interview_conversations(self, application_id: int):
        """면접 대화 전체 조회"""
        # TODO: 실제 데이터 조회 로직 구현
        return {
            "application_id": application_id,
            "conversations": []
        }
    
    def get_applicant_profile_for_company(self, application_id: int):
        """기업용 지원자 프로필 조회"""
        # TODO: 실제 데이터 조회 로직 구현
        return {
            "application_id": application_id,
            "applicant_info": {},
            "documents": [],
            "big5_test_results": {},
            "behavior_test_results": {},
            "own_qnas": []
        }
