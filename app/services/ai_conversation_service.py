from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.job_seeker import JobSeeker
import aiohttp
import json
import logging
import os
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class AIConversationService:
    """면접 대화를 직접 관리 (Facilitator AI 없이 지원자AI ↔ 면접관AI 루프)"""

    def __init__(self, db: Session):
        self.db = db

    # --- 헬퍼 함수 ---
    @staticmethod
    def invoke_lambda_url(url: str, payload: Dict[str, Any], timeout: int = 600) -> Dict[str, Any]:
        """지정된 URL의 Lambda 함수를 호출하고 응답을 반환"""
        headers = {"Content-Type": "application/json"}
        resp = requests.post(url, data=json.dumps(payload), headers=headers, timeout=timeout)
        resp.raise_for_status()
        return resp.json()

    async def conduct_interview(
        self,
        questions: List[str],
        job_seeker: JobSeeker,
        job_posting_skills: Dict[str, Any] = None,
        job_posting_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """지원자AI와 면접관AI를 직접 왕복 호출하여 면접을 진행한다.

        구현 단계 (리턴 구조는 추후 정의):
        0) message_history 초기화
        1) questions 순회
        2) question을 message_history에 추가
        3) 지원자AI 호출 (message_history 마지막 content를 question으로 사용)
        4) 지원자AI 응답 파싱 (answer)
        5) 면접관AI 호출 (initial question + 전체 message_history)
        6) 만족 여부 따라 후속 처리 (불만족 2회 이상이면 다음 질문으로)
        """

        upload_url = os.getenv("UPLOAD_URL")
        applicant_ai_url = os.getenv("APPLICANT_AI_URL")
        interviewer_ai_url = os.getenv("INTERVIEWER_AI_URL")  
        facilitator_ai_url = os.getenv("FACILITATOR_AI_URL")
        knowledge_base_id = os.getenv("KNOWLEDGE_BASE_ID")

        if not upload_url:
            raise Exception("환경변수 UPLOAD_URL이 설정되지 않았습니다.")
        if not applicant_ai_url:
            raise Exception("환경변수 APPLICANT_AI_URL이 설정되지 않았습니다.")
        if not interviewer_ai_url:
            raise Exception("환경변수 INTERVIEWER_AI_URL이 설정되지 않았습니다.")
        if not facilitator_ai_url:
            raise Exception("환경변수 FACILITATOR_AI_URL이 설정되지 않았습니다.")
        if not knowledge_base_id:
            raise Exception("환경변수 KNOWLEDGE_BASE_ID가 설정되지 않았습니다.")
        
        job_seeker_data = self._convert_job_seeker_to_dict(job_seeker)
        name = job_seeker.full_name or f"applicant-{job_seeker.id}"
        
         # 필수 텍스트 검증
        full_text = getattr(job_seeker, 'full_text', None)
        if not full_text:
            raise Exception(f"{name} 사용자 정보로부터 자동 생성을 먼저 진행하세요")
        behavior_text = getattr(job_seeker, 'behavior_text', None)
        if not behavior_text:
            raise Exception(f"{name}의 행동검사를 완료해야 합니다.")
        big5_text = getattr(job_seeker, 'big5_text', None)
        if not big5_text:
            raise Exception(f"{name}의 Big-5 적성검사를 완료해야 합니다.")
        aiqa_text = getattr(job_seeker, 'aiqa_text', None) or ""

        # 업로드 람다 호출
        upload_payload = {
            "user_id": str(job_seeker.id),
            "job_posting_id": str(job_posting_id),
            "full_text": full_text,
            "behavior_text": behavior_text,
            "big5_text": big5_text,
            "aiqa_text": aiqa_text,
            "questions": questions or [],
            "job_postings": {
                "hard_skills": job_posting_skills.get('hard_skills', []) if job_posting_skills else [],
                "soft_skills": job_posting_skills.get('soft_skills', []) if job_posting_skills else []
            },
            "job_seeker_data": {
                "full_name": job_seeker_data.get('full_name') or "",
                "email": job_seeker_data.get('email') or ""
            }
        }

        upload_outputs: Dict[str, Any] = {}
        timeout = aiohttp.ClientTimeout(total=900) # 총 대기 시간을 900초(15분)로 설정
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                logger.info(f"➡️ UPLOAD 호출 (user_id={job_seeker.id}, job_posting_id={job_posting_id})")
                async with session.post(upload_url, json=upload_payload, headers={"Content-Type": "application/json"}) as up_resp:
                    up_status = up_resp.status
                    up_text = await up_resp.text()
                    logger.info(f"UPLOAD response status={up_status} body={up_text}")
                    if up_status < 200 or up_status >= 300:
                        logger.error(f"UPLOAD non-2xx response for {name}: status={up_status}")
                        raise Exception(f"UPLOAD 호출 실패(status={up_status})")
                    try:
                        upload_outputs = json.loads(up_text) if up_text else {}
                    except Exception:
                        upload_outputs = await up_resp.json()

                conversations = upload_outputs.get('conversations') if isinstance(upload_outputs, dict) else None
                if not conversations:
                    conversations = []
                conversation_summary = self._summarize_conversations(conversations) if conversations else ""
        except Exception as e:
            logger.error(f"UPLOAD 호출 실패: {e}")
            raise Exception(f"UPLOAD 호출 실패: {e}")

        user_id = str(job_seeker.id)
        job_postings = {
            "hard_skills": (job_posting_skills or {}).get("hard_skills", []),
            "soft_skills": (job_posting_skills or {}).get("soft_skills", [])
        }

        all_message_histories = {}
        

        # 원 질문들 순회
        for idx, q in enumerate(questions or []):
            message_history: List[Dict[str, Any]] = []  # 질문별 누적 대화
            initial_question = q
            # 2) 질문 추가
            message_history.append({
                "role": "interviewer",  # 질문 역할
                "type": "question",
                "question_number": idx + 1,
                "content": initial_question
            })

            unsatisfied_count = 0
            while True:
                # 3) 지원자 AI 호출 (마지막 메시지가 현재 질문 혹은 follow-up)
                candidate_payload = {
                    "question": message_history[-1]["content"],
                    "knowledge_base_id": knowledge_base_id,
                    "job_posting_id": job_posting_id,
                    "user_id": user_id
                }
                try:
                    logger.info(f"➡️ 지원자AI 호출 (question_number={idx+1}, unsatisfied_count={unsatisfied_count})")
                    candidate_resp = self.invoke_lambda_url(applicant_ai_url, candidate_payload, timeout=900)
                except Exception as e:
                    logger.error(f"지원자AI 호출 실패: {e}")
                    # 실패 시 중단하고 다음 질문으로 넘어갈지 여부는 요구사항 미정. 일단 기록 후 break.
                    message_history.append({
                        "role": "system",
                        "type": "error",
                        "content": f"지원자AI 호출 실패: {e}" 
                    })
                    break

                # 4) 지원자 AI 답변 추출
                applicant_answer = candidate_resp.get("answer")
                if not applicant_answer:
                    # 명세상 answer에 담긴다고 했으나 없어도 방어 로직
                    applicant_answer = json.dumps(candidate_resp, ensure_ascii=False)

                message_history.append({
                    "role": "applicant",
                    "type": "answer",
                    "content": applicant_answer.strip()
                })

                # 5) 면접관AI 호출
                interviewer_payload = {
                    "question": initial_question,
                    "message_history": message_history,  # 누적
                    "job_postings": job_postings
                }

                try:
                    logger.info(f"➡️ 면접관AI 호출 (question_number={idx+1}, attempts={unsatisfied_count+1})")
                    interviewer_resp = self.invoke_lambda_url(interviewer_ai_url, interviewer_payload, timeout=90)
                except Exception as e:
                    logger.error(f"면접관AI 호출 실패: {e}")
                    message_history.append({
                        "role": "system",
                        "type": "error",
                        "content": f"면접관AI 호출 실패: {e}" 
                    })
                    break

                satisfied = interviewer_resp.get("satisfied")

                # 6) 만족 / 불만족 분기
                if satisfied is True:
                    reason = interviewer_resp.get("reason", "")
                    message_history.append({
                        "role": "interviewer",
                        "type": "evaluation",
                        "satisfied": True,
                        "content": reason
                    })
                    logger.info(f"✅ 질문 {idx+1} 만족 (reason length={len(reason)})")
                    break  # 다음 원 질문으로
                else:
                    follow_up = interviewer_resp.get("follow_up_question", "")
                    unsatisfied_count += 1
                    message_history.append({
                        "role": "interviewer",
                        "type": "follow_up",
                        "satisfied": False,
                        "content": follow_up
                    })
                    logger.info(f"➕ 질문 {idx+1} 불만족 -> follow-up 생성 (count={unsatisfied_count})")
                    if unsatisfied_count >= 2:
                        message_history.append({
                            "role": "interviewer",
                            "type": "notice",
                            "content": "반복된 질문에도 지원자AI가 만족스러운 대답을 하지 못했습니다. 다음 질문으로 넘어갑니다"
                        })
                        break  # 다음 질문으로 이동
                    # unsatisfied_count < 2 -> while 루프 지속 (follow_up이 마지막 메시지이므로 재질문)
            all_message_histories[initial_question] = message_history

        # Facilitator AI 호출
        facilitator_input = {
                    "message_history": all_message_histories,
                    "job_postings": job_postings,
                }
        

        timeout = aiohttp.ClientTimeout(total=900) # 총 대기 시간을 900초(15분)로 설정
        async with aiohttp.ClientSession(timeout=timeout) as session:
            logger.info("➡️ FacilitatorAI 호출")
            async with session.post(facilitator_ai_url, json=facilitator_input, headers={"Content-Type": "application/json"}) as fac_resp:
                fac_data = await fac_resp.json()

            if fac_data.get('success', False):
                evaluation = fac_data.get('evaluation', {}) or {}
                message_history = fac_data.get('message_history', conversations) or conversations

                if not evaluation.get('highlight'):
                    logger.warning(f"하이라이트 생성 실패: {e}")

                logger.info("✅ FacilitatorAI 평가 수신 (정규화 완료)")
                return {
                    'success': True,
                    'evaluation': evaluation,
                    'conversations': message_history
                }
            else:
                raise Exception(f"FacilitatorAI 호출 실패: {fac_data}")
    
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
    
    def _summarize_conversations(self, conversations: List[Dict[str, Any]]) -> str:
        """대화 내용 요약"""
        summary = "=== 면접 대화 요약 ===\n"
        
        for conv in conversations:
            summary += f"\n질문 {conv['question_number']}: {conv['question']}\n"
            summary += f"답변: {conv['answer'][:200]}...\n"
            summary += f"상태: {conv['status']} (시도 {conv['attempts']}회)\n"
        
        return summary

    # def _compute_highlights(self, conversations: List[Dict[str, Any]], evaluation: Dict[str, Any]) -> Tuple[str, str]:
    #     """대화에서 평가에 가장 영향을 미친 2~3턴을 선정하여 하이라이트와 이유를 반환합니다.

    #     간단한 휴리스틱:
    #     - evaluation에 'concerns_evidence' 또는 'strengths_evidence'가 있을 경우 그 텍스트에 포함된 문장과 매칭되는 대화를 우선 선택
    #     - 그렇지 않으면, 답변 길이(길수록 상세)와 'status'가 'complete'인 대화를 우선으로 최근 순으로 추출
    #     - 반환: (highlight_text, highlight_reason)
    #     """
    #     if not conversations:
    #         return ("", "")

    #     # 우선 evaluation 기반 evidence 매칭
    #     candidates = []
    #     evidence_pool = []
    #     for key in ('strengths_evidence', 'concerns_evidence', 'followup_evidence'):
    #         v = evaluation.get(key)
    #         if v:
    #             evidence_pool.append(v)

    #     # Flatten conversations into searchable text entries
    #     for conv in conversations:
    #         text = f"Q: {conv.get('question','')} A: {conv.get('answer','')}"
    #         score = 0
    #         # prefer complete answers
    #         if conv.get('status') == 'complete':
    #             score += 10
    #         # longer answers preferred
    #         score += min(len(conv.get('answer','')) // 50, 10)
    #         # recency bonus
    #         score += max(0, 5 - (len(conversations) - conv.get('question_number', 0)))
    #         candidates.append((score, text, conv))

    #     # If evidence_pool exists, prefer conversations that contain evidence substrings
    #     selected = []
    #     if evidence_pool:
    #         for ev in evidence_pool:
    #             for _, text, conv in candidates:
    #                 if ev and ev.strip() and ev in text:
    #                     selected.append((text, f"평가 근거에서 해당 발화가 인용되었습니다: '{ev[:80]}...'") )
    #         # dedupe
    #         selected = list(dict((t, r) for t, r in selected).items())
    #         selected = [(t, r) for t, r in selected]

    #     # fallback: top-scoring conversations
    #     if not selected:
    #         candidates.sort(key=lambda x: x[0], reverse=True)
    #         top = candidates[:3]
    #         selected = [(t, "답변의 구체성과 길이를 기준으로 선정") for _, t, conv in top]

    #     # Build highlight text (concatenate up to 3)
    #     highlight_text = "\n---\n".join([s for s, _ in selected[:3]])
    #     reason_parts = [r for _, r in selected[:3] if r]
    #     highlight_reason = " / ".join(reason_parts) if reason_parts else "선정 기준: 답변의 구체성 및 AI 평가 근거 매칭"

    #     return (highlight_text, highlight_reason)