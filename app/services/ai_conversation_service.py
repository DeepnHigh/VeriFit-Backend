from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.job_seeker import JobSeeker
from app.services.lambda_bedrock_service import LambdaBedrockService
import json
import logging
import aiohttp
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class AIConversationService:
    """LangChain 기반 AI 대화 관리 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
        self.bedrock_service = LambdaBedrockService()
        self.max_retries = 3
        self.min_answer_length = 50  # 최소 답변 길이
        self.max_answer_length = 2000  # 최대 답변 길이
    
    async def conduct_interview(self, questions: List[str], job_seeker: JobSeeker, job_posting_skills: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Lambda를 통한 면접 진행
        
        Args:
            questions: 면접 질문 리스트
            job_seeker: 지원자 정보
            job_posting_skills: 채용공고 스킬 정보
            
        Returns:
            Dict: { success, evaluation, conversations }
        """
        # New flow:
        # 1) Call InterviewTrigger URL to start interview execution and capture executionArn
        # 2) Poll InterviewTrigger (using executionArn) until status == 'SUCCEEDED'
        # 3) When succeeded, call FacilitatorAI URL with required input and return its evaluation + conversations
        INTERVIEW_TRIGGER_URL = os.getenv("INTERVIEW_TRIGGER_URL")
        FACILITATOR_AI_URL = os.getenv("FACILITATOR_AI_URL")

        job_seeker_data = self._convert_job_seeker_to_dict(job_seeker)

        # Ensure we have the detailed texts; require certain fields and raise explicit errors if missing
        name = job_seeker.full_name or f"applicant-{job_seeker.id}"

        full_text = getattr(job_seeker, 'full_text', None)
        if not full_text:
            # 요청: full_text가 없으면 명확한 오류 메시지 반환
            raise Exception(f"{name} 사용자 정보로부터 자동 생성을 먼저 진행하세요")

        behavior_text = getattr(job_seeker, 'behavior_text', None)
        if not behavior_text:
            raise Exception(f"{name}의 행동검사를 완료해야 합니다.")

        big5_text = getattr(job_seeker, 'big5_text', None)
        if not big5_text:
            raise Exception(f"{name}의 Big-5 적성검사를 완료해야 합니다.")

        aiqa_text = getattr(job_seeker, 'aiqa_text', None) or ""

        # Build initial payload for InterviewTrigger per requested format
        start_payload = {
            "user_id": f"applicant-{job_seeker.id}",
            "full_text": full_text,
            "behavior_text": behavior_text,
            "big5_text": big5_text,
            "aiqa_text": aiqa_text,
        }

        execution_arn = None
        interview_outputs: Dict[str, Any] = {}

        try:
            async with aiohttp.ClientSession() as session:
                # Start execution
                logger.info("➡️ InterviewTrigger 시작 요청 전송")
                async with session.post(INTERVIEW_TRIGGER_URL, json=start_payload, headers={"Content-Type": "application/json"}) as resp:
                    start_resp = await resp.json()
                execution_arn = start_resp.get('executionArn') or start_resp.get('execution_arn')
                if not execution_arn:
                    raise Exception(f"InterviewTrigger가 executionArn을 반환하지 않았습니다: {start_resp}")

                logger.info(f"🔖 executionArn: {execution_arn}")

                # Polling loop
                poll_interval = 3  # seconds
                max_polls = 180
                for attempt in range(max_polls):
                    logger.info(f"🔁 실행 상태 폴링 시도 {attempt+1}/{max_polls}")
                    poll_payload = {"executionArn": execution_arn}

                    async with session.post(INTERVIEW_TRIGGER_URL, json=poll_payload, headers={"Content-Type": "application/json"}) as poll_resp:
                        try:
                            poll_data = await poll_resp.json()
                        except Exception:
                            poll_text = await poll_resp.text()
                            raise Exception(f"폴링 응답이 JSON이 아닙니다: {poll_text}")

                    # Accept several possible status keys
                    status = poll_data.get('status') or poll_data.get('executionStatus') or poll_data.get('state') or poll_data.get('statusCode')
                    logger.info(f"폴링 응답 상태: {status}")

                    if isinstance(status, str) and status.upper() in ['SUCCEEDED', 'SUCCESS']:
                        logger.info("✅ InterviewTrigger 실행 완료 (SUCCEEDED)")
                        # capture potential outputs
                        interview_outputs = poll_data.get('output') or poll_data.get('outputs') or poll_data.get('result') or poll_data
                        break

                    # If the trigger returned a final failed state, break with error
                    if isinstance(status, str) and status.upper() in ('FAILED', 'ABORTED', 'TIMED_OUT', 'CANCELLED'):
                        raise Exception(f"Interview execution failed with status: {status}")

                    await asyncio.sleep(poll_interval)
                else:
                    raise Exception("InterviewTrigger가 지정된 시간 내에 완료되지 않았습니다.")

                # Prepare facilitator input
                # Try to extract conversation/message history from interview_outputs
                conversations = interview_outputs.get('conversations') if isinstance(interview_outputs, dict) else None

                # Fallback conversation summary
                if not conversations:
                    # Use the existing summarize helper with minimal structure
                    conversations = []

                conversation_summary = self._summarize_conversations(conversations) if conversations else ""

                facilitator_input = {
                    "user_id": f"applicant-{job_seeker.id}",
                    "questions": questions,
                    "job_seeker_data": {
                        "full_name": job_seeker_data.get('full_name'),
                        "email": job_seeker_data.get('email')
                    },
                    "job_postings": {
                        "hard_skills": job_posting_skills.get('hard_skills', []) if job_posting_skills else [],
                        "soft_skills": job_posting_skills.get('soft_skills', []) if job_posting_skills else []
                    },
                    "full_text": interview_outputs.get('full_text', conversation_summary) if isinstance(interview_outputs, dict) else conversation_summary,
                    "behavior_text": interview_outputs.get('behavior_text', "") if isinstance(interview_outputs, dict) else "",
                    "big5_text": interview_outputs.get('big5_text', "") if isinstance(interview_outputs, dict) else "",
                    "aiqa_text": interview_outputs.get('aiqa_text', "") if isinstance(interview_outputs, dict) else ""
                }

                logger.info("➡️ FacilitatorAI 호출")
                async with session.post(FACILITATOR_AI_URL, json=facilitator_input, headers={"Content-Type": "application/json"}) as fac_resp:
                    fac_data = await fac_resp.json()

                if fac_data.get('success', False):
                    evaluation = fac_data.get('evaluation', {}) or {}
                    message_history = fac_data.get('message_history', conversations) or conversations

                    # Normalize evaluation fields and fill missing pieces
                    # Map possible keys
                    # hard_eval / hard_detail_scores
                    hard_eval = evaluation.get('hard_eval') or evaluation.get('hard_detail_scores') or evaluation.get('hardEval')
                    soft_eval = evaluation.get('soft_eval') or evaluation.get('soft_detail_scores') or evaluation.get('softEval')

                    # Ensure lists
                    if hard_eval is not None and not isinstance(hard_eval, list):
                        try:
                            # if it's a comma-separated string
                            if isinstance(hard_eval, str):
                                hard_eval = [int(x.strip()) for x in hard_eval.split(',') if x.strip().isdigit()]
                            else:
                                hard_eval = list(hard_eval)
                        except Exception:
                            hard_eval = [hard_eval]

                    if soft_eval is not None and not isinstance(soft_eval, list):
                        try:
                            if isinstance(soft_eval, str):
                                soft_eval = [int(x.strip()) for x in soft_eval.split(',') if x.strip().isdigit()]
                            else:
                                soft_eval = list(soft_eval)
                        except Exception:
                            soft_eval = [soft_eval]

                    # Put normalized lists back
                    if hard_eval is not None:
                        evaluation['hard_eval'] = hard_eval
                        evaluation['hard_detail_scores'] = hard_eval
                    if soft_eval is not None:
                        evaluation['soft_eval'] = soft_eval
                        evaluation['soft_detail_scores'] = soft_eval

                    # Fill highlight and highlight_reason if missing
                    if not evaluation.get('highlight'):
                        try:
                            highlight_text, highlight_reason = self._compute_highlights(message_history, evaluation)
                            evaluation['highlight'] = highlight_text
                            evaluation['highlight_reason'] = highlight_reason
                        except Exception as e:
                            logger.warning(f"하이라이트 생성 실패: {e}")

                    logger.info("✅ FacilitatorAI 평가 수신 (정규화 완료)")
                    return {
                        'success': True,
                        'executionArn': execution_arn,
                        'evaluation': evaluation,
                        'conversations': message_history
                    }
                else:
                    raise Exception(f"FacilitatorAI 호출 실패: {fac_data}")

        except Exception as e:
            logger.error(f"❌ conduct_interview 오류: {str(e)}")
            # 기존 동작과 비슷하게 예외로 전달
            raise Exception(f"면접 진행 중 오류가 발생했습니다: {str(e)}")
    
    def _convert_job_seeker_to_dict(self, job_seeker: JobSeeker) -> Dict[str, Any]:
        """JobSeeker 모델을 딕셔너리로 변환"""
        return {
            'id': str(job_seeker.id),
            'full_name': job_seeker.full_name,
            'email': job_seeker.email,
            'phone': job_seeker.phone,
            'location': job_seeker.location,
            'total_experience_years': job_seeker.total_experience_years,
            'company_name': job_seeker.company_name,
            'education_level': job_seeker.education_level,
            'university': job_seeker.university,
            'major': job_seeker.major,
            'graduation_year': job_seeker.graduation_year,
            'bio': job_seeker.bio,
            'portfolios': job_seeker.portfolios or [],
            'resumes': job_seeker.resumes or [],
            'github_repositories': job_seeker.github_repositories or [],
            'certificates': job_seeker.certificates or [],
            'awards': job_seeker.awards or [],
            'qualifications': job_seeker.qualifications or [],
            'papers': job_seeker.papers or [],
            'cover_letters': job_seeker.cover_letters or [],
            'other_documents': job_seeker.other_documents or []
        }
    
    async def _ask_question_with_retry(self, question: str, job_seeker_rag: str, question_number: int) -> Dict[str, Any]:
        """
        재시도를 통한 완전한 답변 보장
        
        Args:
            question: 면접 질문
            job_seeker_rag: 지원자 이력서 RAG
            question_number: 질문 번호
            
        Returns:
            Dict: 질문-답변 대화 정보
        """
        original_question = question
        final_answer = ""
        attempts = 0
        
        for attempt in range(self.max_retries):
            attempts += 1
            logger.info(f"🔄 질문 {question_number} - 시도 {attempt}/{self.max_retries}")
            
            try:
                # 답변 생성
                answer = await self._get_answer(question, job_seeker_rag, question_number)
                final_answer = answer
                
                # 답변 완전성 검사
                if self._is_complete_answer(answer):
                    logger.info(f"✅ 질문 {question_number} 완료 (시도 {attempt}회)")
                    return {
                        "question_number": question_number,
                        "question": original_question,
                        "answer": answer,
                        "attempts": attempts,
                        "status": "complete",
                        "answer_length": len(answer)
                    }
                else:
                    logger.warning(f"⚠️ 질문 {question_number} 불완전한 답변 (시도 {attempt}회)")
                    # 불완전한 답변 시 재시도용 질문 수정
                    question = self._create_followup_question(original_question, answer, attempt)
                    
            except Exception as e:
                logger.error(f"❌ 질문 {question_number} 시도 {attempt} 실패: {str(e)}")
                if attempt < self.max_retries - 1:
                    question = f"{original_question}\n\n이전 답변 생성에 실패했습니다. 다시 답변해주세요."
        
        # 최대 재시도 후에도 불완전한 답변
        logger.warning(f"⚠️ 질문 {question_number} 최대 재시도 후 불완전한 답변")
        return {
            "question_number": question_number,
            "question": original_question,
            "answer": final_answer,
            "attempts": attempts,
            "status": "incomplete",
            "answer_length": len(final_answer) if final_answer else 0
        }
    
    async def _get_answer(self, question: str, job_seeker_rag: str, question_number: int) -> str:
        """지원자 AI를 통해 답변 생성"""
        
        prompt = f"""
당신은 {job_seeker_rag}의 정보를 바탕으로 면접에 응답하는 지원자입니다.

면접 질문: {question}

지원자 정보:
{job_seeker_rag}

위 정보를 바탕으로 자연스럽고 구체적인 답변을 해주세요.
- 실제 경험과 구체적인 사례를 포함해주세요
- 솔직하고 진정성 있는 답변을 해주세요
- 답변은 100자 이상 500자 이하로 작성해주세요

답변:
"""
        
        try:
            response = await self.bedrock_service.generate_interview_answer(prompt)
            
            if response.get('success', False):
                answer = response.get('answer', '')
                logger.info(f"📝 질문 {question_number} 답변 생성 완료 (길이: {len(answer)})")
                return answer
            else:
                raise Exception(f"답변 생성 실패: {response.get('error', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"❌ 답변 생성 중 오류: {str(e)}")
            raise e
    
    def _is_complete_answer(self, answer: str) -> bool:
        """답변의 완전성 검사"""
        if not answer or len(answer.strip()) < self.min_answer_length:
            return False
        
        # 너무 짧은 답변 체크
        if len(answer) < self.min_answer_length:
            return False
        
        # 너무 긴 답변 체크 (토큰 절약)
        if len(answer) > self.max_answer_length:
            return True  # 긴 답변은 완전한 것으로 간주
        
        # 불완전한 답변 패턴 체크
        incomplete_patterns = [
            "모르겠습니다",
            "잘 모르겠어요",
            "답변할 수 없습니다",
            "정보가 없습니다",
            "기억나지 않습니다",
            "답변하기 어렵습니다"
        ]
        
        for pattern in incomplete_patterns:
            if pattern in answer:
                return False
        
        return True
    
    def _create_followup_question(self, original_question: str, previous_answer: str, attempt: int) -> str:
        """재시도용 후속 질문 생성"""
        followup_prompts = [
            f"{original_question}\n\n이전 답변이 너무 간단합니다. 더 구체적이고 자세한 경험을 바탕으로 답변해주세요.",
            f"{original_question}\n\n구체적인 사례나 경험을 포함해서 더 자세히 설명해주세요.",
            f"{original_question}\n\n실제로 겪었던 경험을 바탕으로 더 구체적으로 답변해주세요."
        ]
        
        return followup_prompts[min(attempt - 1, len(followup_prompts) - 1)]
    
    async def _create_job_seeker_rag(self, job_seeker: JobSeeker) -> str:
        """지원자 이력서 RAG 생성"""
        try:
            # 기본 정보
            rag_content = f"""
=== 지원자 기본 정보 ===
이름: {job_seeker.full_name or "정보 없음"}
이메일: {job_seeker.email or "정보 없음"}
전화번호: {job_seeker.phone or "정보 없음"}
위치: {job_seeker.location or "정보 없음"}

=== 경력 정보 ===
총 경력: {job_seeker.total_experience_years or 0}년
최근 직장: {job_seeker.company_name or "정보 없음"}

=== 학력 정보 ===
학력: {job_seeker.education_level or "정보 없음"}
대학교: {job_seeker.university or "정보 없음"}
전공: {job_seeker.major or "정보 없음"}
졸업년도: {job_seeker.graduation_year or "정보 없음"}

=== 자기소개 ===
{job_seeker.bio or "자기소개 없음"}

=== 포트폴리오 ===
"""
            
            # 포트폴리오 정보 추가
            if job_seeker.portfolios:
                try:
                    if isinstance(job_seeker.portfolios, list):
                        for i, portfolio in enumerate(job_seeker.portfolios, 1):
                            rag_content += f"포트폴리오 {i}: {portfolio}\n"
                    else:
                        rag_content += f"포트폴리오: {job_seeker.portfolios}\n"
                except Exception:
                    rag_content += "포트폴리오 정보 파싱 오류\n"
            else:
                rag_content += "포트폴리오 없음\n"
            
            # 이력서 정보 추가
            rag_content += "\n=== 이력서 ===\n"
            if job_seeker.resumes:
                try:
                    if isinstance(job_seeker.resumes, list):
                        for i, resume in enumerate(job_seeker.resumes, 1):
                            rag_content += f"이력서 {i}: {resume}\n"
                    else:
                        rag_content += f"이력서: {job_seeker.resumes}\n"
                except Exception:
                    rag_content += "이력서 정보 파싱 오류\n"
            else:
                rag_content += "이력서 없음\n"
            
            # GitHub 정보 추가
            if job_seeker.github_repositories:
                rag_content += "\n=== GitHub 레포지토리 ===\n"
                try:
                    if isinstance(job_seeker.github_repositories, list):
                        for repo in job_seeker.github_repositories:
                            rag_content += f"- {repo}\n"
                    else:
                        rag_content += f"GitHub: {job_seeker.github_repositories}\n"
                except Exception:
                    rag_content += "GitHub 정보 파싱 오류\n"
            
            # 자격증 정보 추가
            if job_seeker.certificates:
                rag_content += "\n=== 자격증 ===\n"
                try:
                    if isinstance(job_seeker.certificates, list):
                        for cert in job_seeker.certificates:
                            rag_content += f"- {cert}\n"
                    else:
                        rag_content += f"자격증: {job_seeker.certificates}\n"
                except Exception:
                    rag_content += "자격증 정보 파싱 오류\n"
            
            logger.info(f"✅ 지원자 RAG 생성 완료 (길이: {len(rag_content)})")
            return rag_content
            
        except Exception as e:
            logger.error(f"❌ 지원자 RAG 생성 중 오류: {str(e)}")
            return f"지원자 정보: {job_seeker.full_name or '정보 없음'}"
    
    async def _save_conversation_to_db(self, conversation: Dict[str, Any]):
        """대화 내용을 AIInterviewMessage 테이블에 저장"""
        try:
            # TODO: AIInterviewMessage 모델을 사용하여 DB에 저장
            # 현재는 로그만 출력
            logger.info(f"💾 대화 저장: 질문 {conversation['question_number']} - {conversation['status']}")
            
        except Exception as e:
            logger.error(f"❌ 대화 저장 중 오류: {str(e)}")
    
    async def generate_final_evaluation(self, conversations: List[Dict[str, Any]], job_posting_skills: Dict[str, Any]) -> Dict[str, Any]:
        """면접 대화를 바탕으로 최종 평가 결과 생성"""
        try:
            # 대화 내용을 요약
            conversation_summary = self._summarize_conversations(conversations)
            
            # 평가 프롬프트 생성
            evaluation_prompt = f"""
당신은 전문적인 채용 담당자입니다. 다음 면접 대화를 바탕으로 지원자를 정확하게 평가해주세요.

=== 채용공고 요구사항 ===
필수 하드스킬: {', '.join(job_posting_skills.get('hard_skills', []))}
필수 소프트스킬: {', '.join(job_posting_skills.get('soft_skills', []))}

=== 면접 대화 요약 ===
{conversation_summary}

=== 평가 기준 ===
1. 하드스킬 적합성 (0-100점): 요구되는 기술적 역량과 경험의 적합성
2. 소프트스킬 적합성 (0-100점): 커뮤니케이션, 팀워크, 문제해결 능력 등
3. 경험 적합성 (0-100점): 과거 경험이 해당 포지션에 얼마나 적합한지
4. 전체 적합성 (0-100점): 종합적인 적합성 점수

=== 평가 가이드라인 ===
- 답변의 구체성과 진정성을 고려하세요
- 실제 경험과 사례가 포함되었는지 확인하세요
- 요구사항과의 매칭도를 정확히 평가하세요
- 점수는 0-100 사이의 정수로 부여하세요

=== 상세 평가 요구사항 ===
1. strengths_evidence: 강점을 뒷받침하는 구체적인 답변 내용을 인용하세요
2. concerns_evidence: 우려사항을 뒷받침하는 구체적인 답변 내용을 인용하세요
3. followup_content: 추가로 확인해야 할 구체적인 사항들을 제시하세요
4. followup_opinion: 왜 해당 검증이 필요한지 AI 의견을 제시하세요
5. followup_evidence: 후속검증이 필요한 근거를 구체적으로 설명하세요

JSON 형태로 응답해주세요:
{{
    "hard_score": 점수,
    "soft_score": 점수,
    "total_score": 점수,
    "ai_summary": "총평",
    "strengths_content": "강점 내용",
    "strengths_opinion": "강점 AI 의견",
    "strengths_evidence": "강점 근거 (구체적인 답변 내용)",
    "concerns_content": "우려사항 내용", 
    "concerns_opinion": "우려사항 AI 의견",
    "concerns_evidence": "우려사항 근거 (구체적인 답변 내용)",
    "followup_content": "후속검증 제안 내용",
    "followup_opinion": "후속검증 제안 AI 의견",
    "followup_evidence": "후속검증 제안 근거",
    "final_opinion": "최종 의견"
}}
"""
            
            logger.info("🤖 AI 최종 평가 시작")
            
            # Lambda를 통해 평가 실행
            response = await self.bedrock_service.generate_evaluation(evaluation_prompt)
            
            if response.get('success', False):
                evaluation_data = response.get('evaluation', {})
                
                # 평가 데이터 검증
                if self._validate_evaluation_data(evaluation_data):
                    logger.info("✅ AI 평가 성공")
                    return evaluation_data
                else:
                    logger.warning("⚠️ AI 평가 데이터 검증 실패, 기본 평가 사용")
                    return self._get_default_evaluation(conversations)
            else:
                logger.warning("⚠️ AI 평가 실패, 기본 평가 사용")
                return self._get_default_evaluation(conversations)
                
        except Exception as e:
            logger.error(f"❌ 최종 평가 생성 중 오류: {str(e)}")
            return self._get_default_evaluation(conversations)
    
    def _validate_evaluation_data(self, evaluation_data: Dict[str, Any]) -> bool:
        """평가 데이터 유효성 검증"""
        try:
            # 필수 필드 확인
            required_fields = ['hard_score', 'soft_score', 'total_score']
            for field in required_fields:
                if field not in evaluation_data:
                    return False
                
                # 점수 범위 확인 (0-100)
                score = evaluation_data[field]
                if not isinstance(score, (int, float)) or score < 0 or score > 100:
                    return False
            
            # 점수 일관성 확인 (total_score가 hard_score와 soft_score의 평균과 비슷한지)
            hard_score = evaluation_data['hard_score']
            soft_score = evaluation_data['soft_score']
            total_score = evaluation_data['total_score']
            
            expected_total = (hard_score + soft_score) / 2
            if abs(total_score - expected_total) > 20:  # 20점 이상 차이나면 의심
                logger.warning(f"점수 일관성 의심: hard={hard_score}, soft={soft_score}, total={total_score}")
            
            return True
            
        except Exception as e:
            logger.error(f"평가 데이터 검증 중 오류: {str(e)}")
            return False
    
    def _summarize_conversations(self, conversations: List[Dict[str, Any]]) -> str:
        """대화 내용 요약"""
        summary = "=== 면접 대화 요약 ===\n"
        
        for conv in conversations:
            summary += f"\n질문 {conv['question_number']}: {conv['question']}\n"
            summary += f"답변: {conv['answer'][:200]}...\n"
            summary += f"상태: {conv['status']} (시도 {conv['attempts']}회)\n"
        
        return summary

    def _compute_highlights(self, conversations: List[Dict[str, Any]], evaluation: Dict[str, Any]) -> Tuple[str, str]:
        """대화에서 평가에 가장 영향을 미친 2~3턴을 선정하여 하이라이트와 이유를 반환합니다.

        간단한 휴리스틱:
        - evaluation에 'concerns_evidence' 또는 'strengths_evidence'가 있을 경우 그 텍스트에 포함된 문장과 매칭되는 대화를 우선 선택
        - 그렇지 않으면, 답변 길이(길수록 상세)와 'status'가 'complete'인 대화를 우선으로 최근 순으로 추출
        - 반환: (highlight_text, highlight_reason)
        """
        if not conversations:
            return ("", "")

        # 우선 evaluation 기반 evidence 매칭
        candidates = []
        evidence_pool = []
        for key in ('strengths_evidence', 'concerns_evidence', 'followup_evidence'):
            v = evaluation.get(key)
            if v:
                evidence_pool.append(v)

        # Flatten conversations into searchable text entries
        for conv in conversations:
            text = f"Q: {conv.get('question','')} A: {conv.get('answer','')}"
            score = 0
            # prefer complete answers
            if conv.get('status') == 'complete':
                score += 10
            # longer answers preferred
            score += min(len(conv.get('answer','')) // 50, 10)
            # recency bonus
            score += max(0, 5 - (len(conversations) - conv.get('question_number', 0)))
            candidates.append((score, text, conv))

        # If evidence_pool exists, prefer conversations that contain evidence substrings
        selected = []
        if evidence_pool:
            for ev in evidence_pool:
                for _, text, conv in candidates:
                    if ev and ev.strip() and ev in text:
                        selected.append((text, f"평가 근거에서 해당 발화가 인용되었습니다: '{ev[:80]}...'") )
            # dedupe
            selected = list(dict((t, r) for t, r in selected).items())
            selected = [(t, r) for t, r in selected]

        # fallback: top-scoring conversations
        if not selected:
            candidates.sort(key=lambda x: x[0], reverse=True)
            top = candidates[:3]
            selected = [(t, "답변의 구체성과 길이를 기준으로 선정") for _, t, conv in top]

        # Build highlight text (concatenate up to 3)
        highlight_text = "\n---\n".join([s for s, _ in selected[:3]])
        reason_parts = [r for _, r in selected[:3] if r]
        highlight_reason = " / ".join(reason_parts) if reason_parts else "선정 기준: 답변의 구체성 및 AI 평가 근거 매칭"

        return (highlight_text, highlight_reason)
    
    def _get_default_evaluation(self, conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """AI 평가 실패 시 기본 평가 결과 반환 (하드코딩된 점수 사용)"""
        complete_answers = sum(1 for conv in conversations if conv['status'] == 'complete')
        total_questions = len(conversations)
        completion_rate = (complete_answers / total_questions) * 100 if total_questions > 0 else 0
        
        # 완료율에 따른 동적 점수 계산
        base_score = min(completion_rate * 0.8, 85.0)  # 완료율의 80%를 점수로, 최대 85점
        
        return {
            "hard_score": base_score,
            "soft_score": base_score,
            "total_score": base_score,
            "ai_summary": f"면접 완료율 {completion_rate:.1f}%로 기본적인 평가가 완료되었습니다. (AI 평가 실패로 기본 점수 적용)",
            "strengths_content": "면접에 성실히 응답했습니다.",
            "strengths_opinion": "기본적인 소통 능력을 보여주었습니다.",
            "strengths_evidence": "면접 질문에 대해 성실하게 답변했습니다.",
            "concerns_content": "더 구체적인 경험과 역량 확인이 필요합니다.",
            "concerns_opinion": "추가적인 기술적 검증이 필요할 수 있습니다.",
            "concerns_evidence": "일부 질문에 대한 답변이 불완전하거나 구체적이지 않았습니다.",
            "followup_content": "추가 면접이나 기술 테스트를 통한 검증이 필요합니다.",
            "followup_opinion": "더 정확한 평가를 위해 추가 검증이 권장됩니다.",
            "followup_evidence": "현재 면접 결과만으로는 정확한 역량 평가가 어렵습니다.",
            "final_opinion": "기본적인 자격은 갖추었으나, 추가 검증이 필요합니다."
        }
