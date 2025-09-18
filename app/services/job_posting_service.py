from sqlalchemy.orm import Session
from datetime import datetime, date
import json
from typing import Optional, Any, Dict

from app.models.job_posting import JobPosting
from app.models.company import Company
from app.models.ai_overall_report import AIOverallReport

class JobPostingService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_job_postings(self, company_id) -> Dict[str, Any]:
        """채용공고 목록 조회 (회사별)"""
        postings = (
            self.db.query(JobPosting)
            .filter(JobPosting.company_id == company_id)
            .order_by(JobPosting.created_at.desc())
            .all()
        )

        result = []
        for p in postings:
            result.append({
                "id": str(p.id),
                "title": p.title,
                "employment_type": p.employment_type,
                "position_level": p.position_level,
                "salary_min": p.salary_min,
                "salary_max": p.salary_max,
                "is_active": p.is_active,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "application_deadline": p.application_deadline.isoformat() if p.application_deadline else None,
            })

        return {"job_postings": result}
    
    def create_job_posting(self, posting_data: Dict[str, Any], company_id) -> Dict[str, Any]:
        """채용공고 생성 및 저장"""
        # 필드 매핑 및 전처리
        title = posting_data.get("title")
        main_tasks = posting_data.get("main_tasks")

        # requirements: list[str] -> Text(JSON 문자열)로 저장
        requirements_value = posting_data.get("requirements")
        if isinstance(requirements_value, list):
            requirements_text: Optional[str] = json.dumps(requirements_value, ensure_ascii=False)
        elif isinstance(requirements_value, str):
            requirements_text = requirements_value
        else:
            requirements_text = None

        # status: 'active' | 'inactive' -> is_active: bool
        status_value = (posting_data.get("status") or "active").lower()
        is_active = status_value == "active"

        # application_deadline: 'YYYY-MM-DD' -> date
        raw_deadline = posting_data.get("application_deadline")
        application_deadline = None
        if isinstance(raw_deadline, str) and raw_deadline:
            try:
                application_deadline = datetime.strptime(raw_deadline, "%Y-%m-%d").date()
            except ValueError:
                application_deadline = None

        # ai_criteria 처리
        ai_criteria = posting_data.get("ai_criteria") or {}
        hard_skills_value = ai_criteria.get("hard_skills") if isinstance(ai_criteria, dict) else None
        soft_skills_value = ai_criteria.get("soft_skills") if isinstance(ai_criteria, dict) else None

        job_posting = JobPosting(
            company_id=company_id,
            title=title,
            position_level=posting_data.get("position_level"),
            employment_type=posting_data.get("employment_type"),
            location=posting_data.get("location"),
            salary_min=posting_data.get("salary_min"),
            salary_max=posting_data.get("salary_max"),
            main_tasks=main_tasks,
            requirements=requirements_text,
            preferred=posting_data.get("preferred"),
            application_deadline=application_deadline,
            is_active=is_active,
            hard_skills=hard_skills_value if isinstance(hard_skills_value, list) else None,
            soft_skills=soft_skills_value if isinstance(soft_skills_value, list) else None,
        )

        self.db.add(job_posting)
        self.db.commit()
        self.db.refresh(job_posting)

        # 채용공고 생성 시 AI 전체 리포트 초기 레코드도 생성
        try:
            hard_eval_payload = hard_skills_value if isinstance(hard_skills_value, list) else []
            soft_eval_payload = soft_skills_value if isinstance(soft_skills_value, list) else []
            overall_report = AIOverallReport(
                job_posting_id=job_posting.id,
                total_applications=0,
                ai_evaluated_count=0,
                ai_recommended_count=0,
                hard_skill_evaluation={"skills": hard_eval_payload},
                soft_skill_evaluation={"skills": soft_eval_payload},
                overall_review=""
            )
            self.db.add(overall_report)
            self.db.commit()
        except Exception:
            # 리포트 생성 실패는 공고 생성 자체를 막지 않음
            self.db.rollback()

        # 응답 데이터 구성 (requirements는 리스트로 복원)
        response_requirements = []
        if isinstance(requirements_value, list):
            response_requirements = requirements_value
        elif isinstance(requirements_text, str):
            try:
                parsed = json.loads(requirements_text)
                if isinstance(parsed, list):
                    response_requirements = parsed
            except json.JSONDecodeError:
                response_requirements = [requirements_text]

        return {
            "id": str(job_posting.id),
            "company_id": str(job_posting.company_id),
            "title": job_posting.title,
            "position_level": job_posting.position_level,
            "employment_type": job_posting.employment_type,
            "location": job_posting.location,
            "salary_min": job_posting.salary_min,
            "salary_max": job_posting.salary_max,
            "main_tasks": job_posting.main_tasks,
            "requirements": response_requirements,
            "preferred": job_posting.preferred,
            "application_deadline": job_posting.application_deadline.isoformat() if job_posting.application_deadline else None,
            "is_active": job_posting.is_active,
            "status": "active" if job_posting.is_active else "inactive",
            "created_at": job_posting.created_at.isoformat() if job_posting.created_at else None,
            "updated_at": job_posting.updated_at.isoformat() if job_posting.updated_at else None,
            "ai_criteria": {
                "hard_skills": job_posting.hard_skills or [],
                "soft_skills": job_posting.soft_skills or [],
            },
        }
    
    def get_job_posting(self, job_posting_id: str):
        """채용공고 상세 조회 (모든 컬럼 반환)"""
        posting = self.db.query(JobPosting).filter(JobPosting.id == job_posting_id).first()
        if not posting:
            return {
                "error": "not_found",
                "message": "채용공고를 찾을 수 없습니다",
            }

        # requirements 역직렬화
        requirements_list = []
        if isinstance(posting.requirements, str) and posting.requirements:
            try:
                parsed = json.loads(posting.requirements)
                if isinstance(parsed, list):
                    requirements_list = parsed
                else:
                    requirements_list = [posting.requirements]
            except json.JSONDecodeError:
                requirements_list = [posting.requirements]

        return {
            "id": str(posting.id),
            "company_id": str(posting.company_id),
            "title": posting.title,
            "position_level": posting.position_level,
            "employment_type": posting.employment_type,
            "location": posting.location,
            "salary_min": posting.salary_min,
            "salary_max": posting.salary_max,
            "main_tasks": posting.main_tasks,
            "requirements": requirements_list,
            "preferred": posting.preferred,
            "application_deadline": posting.application_deadline.isoformat() if posting.application_deadline else None,
            "is_active": posting.is_active,
            "status": "active" if posting.is_active else "inactive",
            "created_at": posting.created_at.isoformat() if posting.created_at else None,
            "updated_at": posting.updated_at.isoformat() if posting.updated_at else None,
            "ai_criteria": {
                "hard_skills": posting.hard_skills or [],
                "soft_skills": posting.soft_skills or [],
            },
        }
    
    def close_job_posting(self, job_posting_id: int):
        """채용공고 마감"""
        # TODO: JobPosting 모델 구현 후 실제 마감 로직
        return {"message": "채용공고가 마감되었습니다", "job_posting_id": job_posting_id}
    
    def get_public_job_postings(self, include_closed: bool = False) -> Dict[str, Any]:
        """공개 채용공고 목록 조회 (인증 불필요)"""
        try:
            # 기본 쿼리: 회사 정보와 JOIN
            query = (
                self.db.query(JobPosting, Company)
                .join(Company, JobPosting.company_id == Company.id)
                .filter(Company.company_status.is_(None) | (Company.company_status == 'active'))  # NULL이거나 active인 회사
            )
            
            # include_closed가 False인 경우 활성 공고만, 마감일이 지나지 않은 공고만
            if not include_closed:
                today = date.today()
                query = query.filter(
                    JobPosting.is_active == True,
                    JobPosting.application_deadline >= today
                )
            
            # 최신순으로 정렬
            results = query.order_by(JobPosting.created_at.desc()).all()
            
            job_postings = []
            for posting, company in results:
                job_postings.append({
                    "id": str(posting.id),
                    "title": posting.title,
                    "company_id": str(posting.company_id),
                    "company_name": company.company_name,
                    "company": {
                        "company_name": company.company_name,
                        "industry": company.industry,
                        "company_size": company.company_size
                    },
                    "position_level": posting.position_level,
                    "employment_type": posting.employment_type,
                    "location": posting.location,
                    "salary_min": posting.salary_min,
                    "salary_max": posting.salary_max,
                    "main_tasks": posting.main_tasks,
                    "requirements": posting.requirements,
                    "preferred": posting.preferred,
                    "application_deadline": posting.application_deadline.isoformat() if posting.application_deadline else None,
                    "is_active": posting.is_active,
                    "created_at": posting.created_at.isoformat() if posting.created_at else "",
                    "updated_at": posting.updated_at.isoformat() if posting.updated_at else "",
                    "hard_skills": posting.hard_skills or [],
                    "soft_skills": posting.soft_skills or [],
                })
            
            return {
                "success": True,
                "data": job_postings
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": "채용공고를 불러오는데 실패했습니다."
            }
