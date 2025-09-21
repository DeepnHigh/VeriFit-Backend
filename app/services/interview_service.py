from sqlalchemy.orm import Session
from sqlalchemy import func
from decimal import Decimal
import uuid

from app.models.job_posting import JobPosting
from app.models.application import Application
from app.models.job_seeker import JobSeeker
from app.models.ai_evaluation import AIEvaluation
from app.models.ai_overall_report import AIOverallReport
from app.models.big5_test_result import Big5TestResult
from app.models.ai_learning_question import AILearningQuestion
from app.models.ai_learning_answer import AILearningAnswer
from app.models.job_seeker_document import JobSeekerDocument

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
    
    def start_evaluation(self, job_posting_id: str):
        """
        AI 평가 시작 - job_posting의 eval_status를 'ing'로 업데이트
        
        TODO: 
        1. 채용공고별 모든 지원자 조회
        2. 각 지원자별로 AI 대결 시스템 실행
        3. RAG 기반 채용공고 정보 생성 (title, main_tasks, requirements, preferred, hard_skills, soft_skills)
        4. RAG 기반 지원자 정보 생성 (resumes, portfolios, bio, experience 등)
        5. AWS Bedrock Lambda를 통한 AI 평가 실행
        6. 평가 결과를 AIEvaluation 테이블에 저장
        7. 모든 평가 완료 후 eval_status를 'finish'로 업데이트
        """
        try:
            # 공고 존재 확인
            posting = (
                self.db.query(JobPosting)
                .filter(JobPosting.id == job_posting_id)
                .first()
            )
            if not posting:
                return {
                    "status": 404, 
                    "success": False, 
                    "message": "채용공고를 찾을 수 없습니다"
                }
            
            # eval_status를 'ing'로 업데이트
            posting.eval_status = 'ing'
            self.db.commit()
            self.db.refresh(posting)
            
            # TODO: 여기서 실제 AI 평가 로직을 백그라운드에서 실행해야 함
            # 현재는 상태만 업데이트하고 있음
            
            return {
                "status": 200,
                "success": True,
                "message": "AI 평가가 시작되었습니다",
                "data": {
                    "job_posting_id": str(posting.id),
                    "title": posting.title,
                    "eval_status": posting.eval_status
                }
            }
            
        except Exception as e:
            self.db.rollback()
            return {
                "status": 500,
                "success": False,
                "message": f"AI 평가 시작 중 오류가 발생했습니다: {str(e)}"
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
                AIEvaluation.created_at.label("evaluated_at"),
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
                "evaluated_at": r.evaluated_at.isoformat() if r.evaluated_at else None,
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
                    "eval_status": posting.eval_status,
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

    def get_individual_report_by_application(self, application_id: str):
        """applications_id로 application 조회 후 job_seeker.full_name 반환 (임시 버전)

        프론트 요청 경로: /company/interviews/report/{applications_id}
        요구사항: applications_id -> Application -> job_seeker_id -> JobSeeker.full_name
        """
        # application 조회
        application = (
            self.db.query(Application)
            .filter(Application.id == application_id)
            .first()
        )
        if not application:
            return {"status": 404, "success": False, "message": "지원서를 찾을 수 없습니다"}

        # job_seeker 조회
        job_seeker = (
            self.db.query(JobSeeker)
            .filter(JobSeeker.id == application.job_seeker_id)
            .first()
        )
        if not job_seeker:
            return {"status": 404, "success": False, "message": "지원자를 찾을 수 없습니다"}

        full_name = job_seeker.full_name
        # full_name 없으면 이메일 로컬 파트 대체
        if not full_name and getattr(job_seeker, "user", None) and getattr(job_seeker.user, "email", None):
            try:
                full_name = job_seeker.user.email.split("@", 1)[0]
            except Exception:
                full_name = None

        # job_posting 조회 및 스킬 추출
        job_posting = (
            self.db.query(JobPosting)
            .filter(JobPosting.id == application.job_posting_id)
            .first()
        )
        if job_posting:
            hard_skills = job_posting.hard_skills or []
            soft_skills = job_posting.soft_skills or []
        else:
            hard_skills = []
            soft_skills = []

        return {
            "status": 200,
            "success": True,
            "data": {
                "applications_id": str(application.id),
                "job_posting_id": str(application.job_posting_id),
                "job_seeker_id": str(application.job_seeker_id),
                "full_name": full_name,
                "hard_skills": hard_skills,
                "soft_skills": soft_skills,
            },
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

    def get_applicant_profile_by_application(self, application_id: str):
        """applications_id로 지원자 프로필 조회 (임시 버전)

        프론트 요청 경로: /company/interviews/profiles/{applications_id}
        요구사항: applications_id -> Application -> job_seeker_id -> JobSeeker.full_name
        """
        # application 조회
        application = (
            self.db.query(Application)
            .filter(Application.id == application_id)
            .first()
        )
        if not application:
            return {"status": 404, "success": False, "message": "지원서를 찾을 수 없습니다"}

        # job_seeker 조회
        job_seeker = (
            self.db.query(JobSeeker)
            .filter(JobSeeker.id == application.job_seeker_id)
            .first()
        )
        if not job_seeker:
            return {"status": 404, "success": False, "message": "지원자를 찾을 수 없습니다"}

        full_name = job_seeker.full_name
        # full_name 없으면 이메일 로컬 파트 대체
        if not full_name and getattr(job_seeker, "user", None) and getattr(job_seeker.user, "email", None):
            try:
                full_name = job_seeker.user.email.split("@", 1)[0]
            except Exception:
                full_name = None

        # Big5 테스트 결과 조회
        big5_result = (
            self.db.query(Big5TestResult)
            .filter(Big5TestResult.job_seeker_id == job_seeker.id)
            .order_by(Big5TestResult.test_date.desc())
            .first()
        )
        
        big5_test_results = {}
        if big5_result:
            big5_test_results = {
                "id": str(big5_result.id),
                "test_date": big5_result.test_date.isoformat() if big5_result.test_date else None,
                "scores": {
                    "openness": float(big5_result.openness_score) if big5_result.openness_score else None,
                    "conscientiousness": float(big5_result.conscientiousness_score) if big5_result.conscientiousness_score else None,
                    "extraversion": float(big5_result.extraversion_score) if big5_result.extraversion_score else None,
                    "agreeableness": float(big5_result.agreeableness_score) if big5_result.agreeableness_score else None,
                    "neuroticism": float(big5_result.neuroticism_score) if big5_result.neuroticism_score else None,
                },
                "levels": {
                    "openness": big5_result.openness_level,
                    "conscientiousness": big5_result.conscientiousness_level,
                    "extraversion": big5_result.extraversion_level,
                    "agreeableness": big5_result.agreeableness_level,
                    "neuroticism": big5_result.neuroticism_level,
                },
                "interpretations": big5_result.interpretations,
            }

        # AI 학습 질문과 답변 조회 (답변이 있는 것만)
        # UUID 타입으로 변환해서 시도
        job_seeker_uuid = uuid.UUID(str(job_seeker.id))
        
        ai_qnas = (
            self.db.query(AILearningQuestion, AILearningAnswer)
            .join(AILearningAnswer, AILearningAnswer.question_id == AILearningQuestion.id)
            .filter(AILearningAnswer.job_seeker_id == job_seeker_uuid)
            .order_by(AILearningQuestion.display_order, AILearningAnswer.response_date)
            .all()
        )
        
        own_qnas = []
        for question, answer in ai_qnas:
            own_qnas.append({
                "question_id": str(question.id),
                "question_text": question.question_text,
                "answer_id": str(answer.id),
                "answer_text": answer.answer_text,
                "response_date": answer.response_date.isoformat() if answer.response_date else None,
            })

        # 지원자 문서 조회
        documents = (
            self.db.query(JobSeekerDocument)
            .filter(JobSeekerDocument.job_seeker_id == job_seeker_uuid)
            .order_by(JobSeekerDocument.uploaded_at.desc())
            .all()
        )
        
        documents_list = []
        for doc in documents:
            documents_list.append({
                "id": str(doc.id),
                "document_type": doc.document_type,
                "file_name": doc.file_name,
                "file_url": doc.file_url,
                "file_size": doc.file_size,
                "mime_type": doc.mime_type,
                "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
            })

        # 디버깅: behavior_text 확인
        behavior_text = getattr(job_seeker, "behavior_text", None)
        print(f"DEBUG: behavior_text = {behavior_text}")
        
        # 만약 None이면 직접 조회
        if behavior_text is None:
            from sqlalchemy import text
            result = self.db.execute(text("SELECT behavior_text FROM job_seekers WHERE id = :id"), {"id": str(job_seeker.id)})
            row = result.fetchone()
            if row:
                behavior_text = row[0]
                print(f"DEBUG: Direct query behavior_text = {behavior_text}")

        return {
            "status": 200,
            "success": True,
            "data": {
                "application_id": str(application.id),
                "job_posting_id": str(application.job_posting_id),
                "job_seeker_id": str(application.job_seeker_id),
                "full_name": full_name,
                "applicant_info": {
                    "full_name": full_name,
                    "email": getattr(job_seeker, "email", None),
                    "phone": getattr(job_seeker, "phone", None),
                    "education_level": getattr(job_seeker, "education_level", None),
                    "university": getattr(job_seeker, "university", None),
                    "major": getattr(job_seeker, "major", None),
                    "graduation_year": getattr(job_seeker, "graduation_year", None),
                    "total_experience_year": getattr(job_seeker, "total_experience_year", None),
                    "company_name": getattr(job_seeker, "company_name", None),
                    "bio": getattr(job_seeker, "bio", None),
                },
                "documents": documents_list,
                "big5_test_results": big5_test_results,
                "behavior_test_results": {
                    "behavior_text": behavior_text
                },
                "own_qnas": own_qnas
            },
        }
