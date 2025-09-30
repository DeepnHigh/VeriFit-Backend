from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from decimal import Decimal
import uuid

from app.models.job_posting import JobPosting
from app.models.application import Application
from app.models.job_seeker import JobSeeker
from app.models.ai_evaluation import AIEvaluation
from app.models.ai_interview_message import AIInterviewMessage
from app.models.ai_overall_report import AIOverallReport
from app.models.big5_test_result import Big5TestResult
from app.models.ai_learning_question import AILearningQuestion
from app.models.ai_learning_answer import AILearningAnswer
from app.models.job_seeker_document import JobSeekerDocument
from app.services.interview_question_service import InterviewQuestionService
from app.services.lambda_bedrock_service import LambdaBedrockService
import logging

# Lazy load AIConversationService to avoid circular imports
def get_ai_conversation_service():
    from app.services.ai_conversation_service import AIConversationService
    return AIConversationService

logger = logging.getLogger(__name__)

class InterviewService:
    def __init__(self, db: Session):
        self.db = db
    
    async def start_evaluation(self, job_posting_id: str, force: bool = False):
        """AI 평가 프로세스 시작 (새로운 프로세스)"""
        try:
            # 1. 채용공고 조회
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
            
            # 2. 평가 상태 확인 (중복 실행 방지)
            if posting.eval_status == 'ing':
                # 기존에는 중복 실행 시 409로 막았으나, 운영상 강제 시작 필요가 있어 로그만 남기고 계속 진행합니다.
                # 향후 force 플래그를 활용해 더 세밀한 제어를 할 수 있습니다.
                logger.warning(f"평가가 이미 진행 중입니다. force={force} - 계속 진행합니다.")
            
            logger.info(f"평가 상태 변경: {posting.eval_status} -> ing")
            
            # 3. eval_status를 'ing'로 업데이트
            posting.eval_status = 'ing'
            self.db.commit()
            self.db.refresh(posting)
            
            # 3. 지원자 목록 조회
            applications = (
                self.db.query(Application)
                .filter(Application.job_posting_id == job_posting_id)
                .all()
            )
            
            logger.info(f"[DEBUG] 지원자 수: {len(applications)}")
            for app in applications:
                logger.debug(f"[DEBUG] Application ID: {app.id}, Job Seeker ID: {app.job_seeker_id}")
            
            if not applications:
                # 지원자가 없는 경우
                posting.eval_status = 'finish'
                self.db.commit()
                return {
                    "status": 200,
                    "success": True,
                    "message": "지원자가 없어 평가를 완료했습니다",
                    "data": {
                        "job_posting_id": str(posting.id),
                        "title": posting.title,
                        "eval_status": posting.eval_status,
                        "evaluated_count": 0
                    }
                }
            
            # 4. 면접 질문 생성 (DB에 저장됨)
            question_service = InterviewQuestionService(self.db)
            # generate_interview_questions is async; await it
            questions = await question_service.generate_interview_questions(posting)
            # Defensive: if a coroutine slipped through, await it
            if hasattr(questions, '__await__'):
                questions = await questions
            # If the bedrock wrapper returned a dict with 'questions', extract it
            if isinstance(questions, dict) and questions.get('questions') is not None:
                questions = questions.get('questions') or []
            # Fallback to default list if still falsy
            if not questions:
                questions = question_service._get_default_questions(posting)
                posting.interview_questions = questions
                self.db.commit()
            
            # 5. 각 지원자별로 aiqa_text 생성/DB 저장 처리
            for application in applications:
                try:
                    job_seeker = (
                        self.db.query(JobSeeker)
                        .filter(JobSeeker.id == application.job_seeker_id)
                        .first()
                    )
                    if not job_seeker:
                        logger.warning(f"Job Seeker를 찾을 수 없음 - Application ID: {application.id}, Job Seeker ID: {application.job_seeker_id}")
                        continue
                    
                    logger.info(f"지원자 {job_seeker.id} 처리 시작")
                    logger.debug(f"Job Seeker 정보: ID={job_seeker.id}, Name={getattr(job_seeker, 'name', 'N/A')}")
                    
                    # 5-1. AI Q&A 텍스트 생성 및 DB 저장
                    try:
                        logger.debug(f"AI Q&A 조회 시작 - Job Seeker ID: {job_seeker.id} (type={type(job_seeker.id)})")
                        
                        ai_qnas = (
                            self.db.query(AILearningQuestion, AILearningAnswer)
                            .join(AILearningAnswer, AILearningAnswer.question_id == AILearningQuestion.id)
                            .filter(AILearningAnswer.job_seeker_id == job_seeker.id)
                            .order_by(AILearningQuestion.display_order, AILearningAnswer.response_date)
                            .all()
                        )
                        logger.debug(f"AI Q&A 조회 결과: {len(ai_qnas)}개")
                        
                        qa_lines = []
                        for question, answer in ai_qnas:
                            q_text = (question.question_text or "").strip()
                            a_text = (answer.answer_text or "").strip()
                            if q_text and a_text:
                                qa_lines.append(f"질문: {q_text}\n답변: {a_text}")
                        
                        aiqa_text = "\n\n".join(qa_lines) if qa_lines else ""
                        logger.debug(f"생성된 aiqa_text 길이: {len(aiqa_text)}")
                        
                        existing_aiqa_text = getattr(job_seeker, "aiqa_text", None)
                        logger.debug(f"기존 aiqa_text 길이: {len(existing_aiqa_text) if existing_aiqa_text else 0}")
                        
                        if aiqa_text != (existing_aiqa_text or ""):
                            logger.debug(f"aiqa_text DB 저장 시작")
                            job_seeker.aiqa_text = aiqa_text
                            self.db.commit()
                            self.db.refresh(job_seeker)
                            logger.debug(f"aiqa_text DB 저장 완료 (길이: {len(job_seeker.aiqa_text or '')})")
                        else:
                            logger.debug(f"aiqa_text 저장 건너뜀 (변경 없음)")
                            
                    except Exception as e:
                        logger.warning(f"aiqa_text 생성 중 오류: {str(e)}")
                        # 오류 시에도 기존 값 사용
                        aiqa_text = getattr(job_seeker, "aiqa_text", None) or ""
                    
                    logger.info(f"지원자 {job_seeker.id} aiqa_text 처리 완료")
                    
                except Exception as e:
                    logger.error(f"지원자 {application.id} aiqa_text 처리 실패: {str(e)}")
                    continue

            # 6. 각 지원자별로 면접 진행
            try:
                logger.info("AIConversationService 초기화 시작")
                AIConversationService = get_ai_conversation_service()
                conversation_service = AIConversationService(self.db)
                logger.info("AIConversationService 초기화 완료")
            except Exception as e:
                logger.error(f"AIConversationService 초기화 실패: {str(e)}")
                raise Exception(f"AIConversationService 초기화 실패: {str(e)}")
            
            evaluated_count = 0
            total_apps = len(applications)
            logger.info(f"면접 평가 시작: 총 지원자 {total_apps}명")

            for idx, application in enumerate(applications, start=1):
                try:
                    logger.info(f"({idx}/{total_apps}) 지원자 평가 시작 - Application ID: {application.id}")
                    # _evaluate_application is now async to allow awaiting safely
                    await self._evaluate_application(
                        application, questions, conversation_service, posting
                    )
                    evaluated_count += 1
                    logger.info(f"({idx}/{total_apps}) 지원자 평가 완료 - Application ID: {application.id}")
                except Exception as e:
                    # 개별 지원자 평가 실패는 전체 프로세스를 중단하지 않음
                    logger.error(f"지원자 {application.id} 평가 실패: {str(e)}")
                    import traceback
                    logger.error(f"지원자 {application.id} 평가 실패 - 상세 에러: {traceback.format_exc()}")
                    continue
            
            # 8. 모든 평가 완료 후 상태 업데이트
            posting.eval_status = 'finish'
            self.db.commit()
            
            return {
                "status": 200,
                "success": True,
                "message": f"AI 평가 완료! (지원자 {len(applications)}명, 평가 완료 {evaluated_count}명)",
                "data": {
                    "job_posting_id": str(posting.id),
                    "title": posting.title,
                    "eval_status": posting.eval_status,
                    "questions_generated": len(questions),
                    "total_applications": len(applications),
                    "evaluated_count": evaluated_count
                }
            }
            
        except Exception as e:
            self.db.rollback()
            import traceback
            logger.error(f"AI 평가 시작 중 전체 오류 발생: {str(e)}")
            logger.error(f"AI 평가 시작 중 전체 오류 - 상세 traceback: {traceback.format_exc()}")
            return {
                "status": 500,
                "success": False,
                "message": f"AI 평가 시작 중 오류가 발생했습니다: {str(e)}"
            }
    
    async def _evaluate_application(self, application: Application, questions: list, conversation_service: Any, job_posting: JobPosting):
        try:
            hard_skills = job_posting.hard_skills or []
            soft_skills = job_posting.soft_skills or []
            # 1. 지원자 정보 조회
            job_seeker = (
                self.db.query(JobSeeker)
                .filter(JobSeeker.id == application.job_seeker_id)
                .first()
            )
            
            if not job_seeker:
                raise Exception(f"지원자 정보를 찾을 수 없습니다: {application.job_seeker_id}")
            
            # 2. 면접 대화 진행
            if not job_posting:
                raise Exception(f"Job posting 정보를 찾을 수 없습니다: {application.job_posting_id}")
            job_posting_skills = {
                "hard_skills": job_posting.hard_skills or [],
                "soft_skills": job_posting.soft_skills or []
            }
            # 1) conduct_interview now synchronous and performs upload
            interview_result = conversation_service.conduct_interview(questions, job_seeker, job_posting_skills, job_posting_id=str(job_posting.id))
            # Defensive: if the service returned a coroutine/awaitable, await it
            if hasattr(interview_result, '__await__'):
                interview_result = await interview_result
            conversations = interview_result.get('conversations', [])
            # If conduct_interview didn't include facilitator evaluation, call evaluate_with_facilitator
            evaluation_result = interview_result.get('evaluation', {})
            if not evaluation_result:
                try:
                    fac_call = conversation_service.evaluate_with_facilitator(application, questions, job_seeker, job_posting_skills, job_posting_id=str(job_posting.id), interview_outputs=interview_result)
                    if hasattr(fac_call, '__await__'):
                        await fac_call
                    # refresh evaluation_result from DB
                    evaluation_result = (
                        self.db.query(AIEvaluation)
                        .filter(AIEvaluation.application_id == application.id)
                        .order_by(AIEvaluation.created_at.desc())
                        .first()
                    )
                    if evaluation_result:
                        # convert to dict-like for downstream
                        evaluation_result = {
                            'hard_score': evaluation_result.hard_score,
                            'soft_score': evaluation_result.soft_score,
                            'total_score': evaluation_result.total_score,
                            'ai_summary': evaluation_result.ai_summary,
                            'hard_detail_scores': evaluation_result.hard_detail_scores,
                            'soft_detail_scores': evaluation_result.soft_detail_scores,
                            'highlight': evaluation_result.highlight,
                            'highlight_reason': evaluation_result.highlight_reason,
                        }
                    else:
                        evaluation_result = {}
                except Exception as e:
                    logger.error(f"Facilitator 평가 중 오류: {e}")
                    evaluation_result = {}
            
            # 4. AIEvaluation 테이블 업서트(있으면 업데이트, 없으면 생성)
            existing_ai_evaluation = (
                self.db.query(AIEvaluation)
                .filter(AIEvaluation.application_id == application.id)
                .first()
            )

            hard_score = Decimal(str(evaluation_result.get('hard_score', 0.0)))
            soft_score = Decimal(str(evaluation_result.get('soft_score', 0.0)))
            total_score = Decimal(str(evaluation_result.get('total_score', 0.0)))
            ai_summary = evaluation_result.get('ai_summary', 'AI 평가 결과 없음')
            strengths_content = evaluation_result.get('strengths_content', '')
            strengths_opinion = evaluation_result.get('strengths_opinion', '')
            strengths_evidence = evaluation_result.get('strengths_evidence', '')
            concerns_content = evaluation_result.get('concerns_content', '')
            concerns_opinion = evaluation_result.get('concerns_opinion', '')
            concerns_evidence = evaluation_result.get('concerns_evidence', '')
            followup_content = evaluation_result.get('followup_content', '')
            followup_opinion = evaluation_result.get('followup_opinion', '')
            followup_evidence = evaluation_result.get('followup_evidence', '')
            final_opinion = evaluation_result.get('final_opinion', '')
            highlight_text = evaluation_result.get('highlight') or evaluation_result.get('interview_highlights') or None
            highlight_reason = evaluation_result.get('highlight_reason') or None

            if existing_ai_evaluation:
                existing_ai_evaluation.hard_score = hard_score
                existing_ai_evaluation.soft_score = soft_score
                existing_ai_evaluation.total_score = total_score
                existing_ai_evaluation.ai_summary = ai_summary
                # 하드/소프트 상세 분석 필드 저장 (Facilitator 또는 평가 결과에서 제공되는 키 확인)
                # hard_detail_scores/soft_detail_scores가 list로 올 경우 dict로 변환
                def _normalize_detail_scores(detail, skills):
                    if isinstance(detail, dict):
                        return detail
                    if isinstance(detail, list) and isinstance(skills, list):
                        return {str(sk): detail[idx] if idx < len(detail) else None for idx, sk in enumerate(skills)}
                    return None

                hard_detail_raw = evaluation_result.get('hard_detail_scores') or evaluation_result.get('hard_eval') or None
                soft_detail_raw = evaluation_result.get('soft_detail_scores') or evaluation_result.get('soft_eval') or None
                existing_ai_evaluation.hard_detail_scores = _normalize_detail_scores(hard_detail_raw, hard_skills)
                existing_ai_evaluation.soft_detail_scores = _normalize_detail_scores(soft_detail_raw, soft_skills)
                existing_ai_evaluation.strengths_content = strengths_content
                existing_ai_evaluation.strengths_opinion = strengths_opinion
                existing_ai_evaluation.strengths_evidence = strengths_evidence
                existing_ai_evaluation.concerns_content = concerns_content
                existing_ai_evaluation.concerns_opinion = concerns_opinion
                existing_ai_evaluation.concerns_evidence = concerns_evidence
                existing_ai_evaluation.followup_content = followup_content
                existing_ai_evaluation.followup_opinion = followup_opinion
                existing_ai_evaluation.followup_evidence = followup_evidence
                existing_ai_evaluation.final_opinion = final_opinion
                existing_ai_evaluation.highlight = highlight_text
                existing_ai_evaluation.highlight_reason = highlight_reason
                # 재평가 시점으로 타임스탬프 갱신
                existing_ai_evaluation.created_at = func.now()
            else:
                ai_evaluation = AIEvaluation(
                    application_id=application.id,
                    hard_score=hard_score,
                    soft_score=soft_score,
                    total_score=total_score,
                    ai_summary=ai_summary,
                    hard_detail_scores=(evaluation_result.get('hard_detail_scores') or evaluation_result.get('hard_eval') or None),
                    soft_detail_scores=(evaluation_result.get('soft_detail_scores') or evaluation_result.get('soft_eval') or None),
                    strengths_content=strengths_content,
                    strengths_opinion=strengths_opinion,
                    strengths_evidence=strengths_evidence,
                    concerns_content=concerns_content,
                    concerns_opinion=concerns_opinion,
                    concerns_evidence=concerns_evidence,
                    followup_content=followup_content,
                    followup_opinion=followup_opinion,
                    followup_evidence=followup_evidence,
                    final_opinion=final_opinion,
                    highlight=highlight_text,
                    highlight_reason=highlight_reason,
                )
                self.db.add(ai_evaluation)

            # 4.5 ai_interview_messages 테이블에 대화 저장
            try:
                # 기존 메시지 제거(중복 삽입 방지)
                self.db.query(AIInterviewMessage).filter(AIInterviewMessage.application_id == application.id).delete()
                # conversations는 conduct_interview에서 전달된 message list
                for conv in (conversations or []):
                    try:
                        # 일부 소스(conduct_interview)에서는 'role' 키만 존재하므로 fallback 처리
                        sender_raw = (conv.get('sender') or conv.get('role') or '').lower()
                        if sender_raw in ('interviewer','interviewer_ai','facilitator','reviewer'):
                            sender = 'interviewer_ai'
                        elif sender_raw in ('applicant','candidate','candidate_ai','user','answer'):
                            sender = 'candidate_ai'
                        elif sender_raw in ('system','notice','error','question'):
                            # 시스템/질문 메시지는 면접관 측으로 분류 (별도 enum 추가 전 임시 정책)
                            sender = 'interviewer_ai'
                        else:
                            # 미지정 값 기본 지원자 측
                            sender = 'candidate_ai'
                        message_type = conv.get('message_type') or 'other'
                        content = conv.get('content') or ''
                        turn_number = conv.get('turn_number') or conv.get('question_number') or 0
                        highlight_turns = conv.get('highlight_turns') or conv.get('highlight_turns')

                        msg = AIInterviewMessage(
                            application_id=application.id,
                            sender=sender,
                            message_type=message_type,
                            content=content,
                            turn_number=turn_number,
                            highlight_turns=highlight_turns,
                        )
                        self.db.add(msg)
                    except Exception as e:
                        logger.warning(f"AIInterviewMessage 생성 중 개별 오류: {e}")
            except Exception as e:
                logger.warning(f"ai_interview_messages 저장 중 오류: {e}")
            
            # 5. 지원서 상태 업데이트
            application.application_status = 'ai_evaluated'
            application.evaluated_at = func.now()
            
            self.db.commit()
            
            print(f"✅ 지원자 {job_seeker.full_name} 평가 완료")
            
        except Exception as e:
            self.db.rollback()
            raise Exception(f"지원자 평가 중 오류: {str(e)}")
    
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

        # 지원 목록 조인 조회 - 중복 방지를 위해 서브쿼리로 최신 application만 선택
        # 각 job_seeker별로 최신 application만 선택하는 서브쿼리
        latest_applications = (
            self.db.query(
                Application.job_seeker_id,
                func.max(Application.applied_at).label('latest_applied_at')
            )
            .filter(Application.job_posting_id == job_posting_id)
            .group_by(Application.job_seeker_id)
            .subquery()
        )
        
        rows = (
            self.db.query(
                Application.id.label("application_id"),
                JobSeeker.user_id.label("user_id"),
                JobSeeker.full_name.label("candidate_name"),
                Application.applied_at.label("applied_at"),
                Application.application_status.label("stage"),
                Application.evaluated_at.label("evaluated_at"),
            )
            .join(JobSeeker, JobSeeker.id == Application.job_seeker_id)
            .join(latest_applications, 
                  (Application.job_seeker_id == latest_applications.c.job_seeker_id) & 
                  (Application.applied_at == latest_applications.c.latest_applied_at))
            .filter(Application.job_posting_id == job_posting_id)
            .order_by(Application.applied_at.desc())
            .all()
        )

        applications = []
        for r in rows:
            # 각 application에 대한 최신 AI evaluation 조회
            latest_eval = (
                self.db.query(AIEvaluation)
                .filter(AIEvaluation.application_id == r.application_id)
                .order_by(AIEvaluation.created_at.desc())
                .first()
            )
            
            overall_score_val = None
            hard_score_val = None
            soft_score_val = None
            ai_summary_val = None
            
            if latest_eval:
                if latest_eval.total_score is not None:
                    try:
                        overall_score_val = int(Decimal(latest_eval.total_score))
                    except Exception:
                        overall_score_val = float(latest_eval.total_score)
                if latest_eval.hard_score is not None:
                    try:
                        hard_score_val = float(latest_eval.hard_score)
                    except Exception:
                        hard_score_val = None
                if latest_eval.soft_score is not None:
                    try:
                        soft_score_val = float(latest_eval.soft_score)
                    except Exception:
                        soft_score_val = None
                ai_summary_val = latest_eval.ai_summary

            applications.append({
                "applications_id": str(r.application_id),
                "user_id": str(r.user_id) if r.user_id else None,
                "candidate_name": r.candidate_name,
                "applied_at": r.applied_at.isoformat() if r.applied_at else None,
                "stage": r.stage,
                "overall_score": overall_score_val,
                "hard_score": hard_score_val,
                "soft_score": soft_score_val,
                "ai_summary": ai_summary_val,
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

        # ai_evaluations 조회 (해당 application의 최신 평가 1건)
        ai_eval_row = (
            self.db.query(AIEvaluation)
            .filter(AIEvaluation.application_id == application.id)
            .order_by(AIEvaluation.created_at.desc())
            .first()
        )

        ai_evaluation = None
        if ai_eval_row:
            # Decimal -> float 변환 및 직렬화 가능한 형태로 변환
            def _to_float(val):
                try:
                    return float(val) if val is not None else None
                except Exception:
                    return None

            def _to_str(val):
                if isinstance(val, str):
                    return val
                if val is None:
                    return ""
                if isinstance(val, list):
                    return "\n---\n".join([_to_str(v) for v in val])
                if isinstance(val, dict):
                    # dict의 주요 텍스트 값만 추출 (예: chat, text, content)
                    for k in ["chat", "text", "content"]:
                        if k in val:
                            return _to_str(val[k])
                    return str(val)
                try:
                    return str(val)
                except Exception:
                    return ""

            ai_evaluation = {
                "id": str(ai_eval_row.id),
                "hard_score": _to_float(ai_eval_row.hard_score),
                "soft_score": _to_float(ai_eval_row.soft_score),
                "total_score": _to_float(ai_eval_row.total_score),
                "ai_summary": ai_eval_row.ai_summary,
                "hard_detail_scores": ai_eval_row.hard_detail_scores,
                "soft_detail_scores": ai_eval_row.soft_detail_scores,
                "highlight": _to_str(ai_eval_row.highlight),
                "highlight_reason": _to_str(ai_eval_row.highlight_reason),
                "strengths_content": ai_eval_row.strengths_content,
                "strengths_opinion": ai_eval_row.strengths_opinion,
                "strengths_evidence": ai_eval_row.strengths_evidence,
                "concerns_content": ai_eval_row.concerns_content,
                "concerns_opinion": ai_eval_row.concerns_opinion,
                "concerns_evidence": ai_eval_row.concerns_evidence,
                "followup_content": ai_eval_row.followup_content,
                "followup_opinion": ai_eval_row.followup_opinion,
                "followup_evidence": ai_eval_row.followup_evidence,
                "final_opinion": ai_eval_row.final_opinion,
                "created_at": ai_eval_row.created_at.isoformat() if getattr(ai_eval_row, "created_at", None) else None,
            }
        # ai_interview_messages 조회 (전체 대화)
        messages = (
            self.db.query(AIInterviewMessage)
            .filter(AIInterviewMessage.application_id == application.id)
            .order_by(AIInterviewMessage.turn_number.asc())
            .all()
        )

        conversations = []
        for m in messages:
            # 변환 없이 DB의 sender(interviewer_ai / candidate_ai) 그대로 전달
            conversations.append({
                "id": str(m.id),
                "sender": m.sender,
                "message_type": m.message_type,
                "content": m.content,
                "turn_number": m.turn_number,
                "highlight_turns": m.highlight_turns,
                "created_at": m.created_at.isoformat() if getattr(m, "created_at", None) else None,
            })

        # highlight 텍스트가 있으면 간단하게 채팅 형식으로 변환해서 interview_highlights에 포함
        interview_highlights = []
        if ai_evaluation and ai_evaluation.get('highlight'):
            try:
                parts = ai_evaluation.get('highlight').split('\n---\n')
                for p in parts:
                    text_block = p.strip()
                    # 역할 추정은 하지 않고 원문만 전달 (프론트가 필요 시 문자열 패턴/Q:,A: 여부로 자체 판단)
                    interview_highlights.append({
                        "chat": text_block
                    })
            except Exception:
                interview_highlights = [{"chat": ai_evaluation.get('highlight') }]

        # 최종 응답
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
                "ai_evaluation": ai_evaluation,
                "conversations": conversations,
                # 프론트 호환을 위해 기존 문자열 형태 유지 + 추가로 structured_highlights를 내려줄 수도 있음
                "interview_highlights": (
                    "\n---\n".join([_to_str(h.get("chat")) for h in interview_highlights]) if isinstance(interview_highlights, list) else _to_str(interview_highlights)
                ),
                "structured_highlights": interview_highlights,
            },
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