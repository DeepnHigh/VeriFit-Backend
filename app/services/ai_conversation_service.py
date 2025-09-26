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
    
    async def conduct_interview(
        self,
        questions: List[str],
        job_seeker: JobSeeker,
        job_posting_skills: Dict[str, Any] = None,
        job_posting_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        업로드 람다(UPLOAD_URL) → FacilitatorAI 순으로만 호출하여 면접 평가를 수행합니다.

        Returns: { success, evaluation, conversations }
        """
        UPLOAD_URL = os.getenv("UPLOAD_URL")
        FACILITATOR_AI_URL = os.getenv("FACILITATOR_AI_URL")

        if not UPLOAD_URL:
            raise Exception("환경변수 UPLOAD_URL이 설정되지 않았습니다.")
        if not FACILITATOR_AI_URL:
            raise Exception("환경변수 FACILITATOR_AI_URL이 설정되지 않았습니다.")

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

        # 1) 업로드 람다 호출
        upload_payload = {
            "user_id": f"applicant-{job_seeker.id}",
            "full_text": full_text,
            "behavior_text": behavior_text,
            "big5_text": big5_text,
            "aiqa_text": aiqa_text,
            # 선택적으로 전달 (람다가 이해한다면):
            "questions": questions or [],
            "job_postings": {
                "hard_skills": job_posting_skills.get('hard_skills', []) if job_posting_skills else [],
                "soft_skills": job_posting_skills.get('soft_skills', []) if job_posting_skills else []
            },
            # 하위 시스템에서 필요할 수 있는 식별자 (호환성 유지 목적)
            "job_posting_id": job_posting_id,
            "job_seeker_data": {
                "full_name": job_seeker_data.get('full_name') or "",
                "email": job_seeker_data.get('email') or ""
            }
        }

        upload_outputs: Dict[str, Any] = {}
        timeout = aiohttp.ClientTimeout(total=900) # 총 대기 시간을 900초(15분)로 설정
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                logger.info("➡️ UPLOAD 호출")
                async with session.post(UPLOAD_URL, json=upload_payload, headers={"Content-Type": "application/json"}) as up_resp:
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

                # 2) FacilitatorAI 호출
                conversations = upload_outputs.get('conversations') if isinstance(upload_outputs, dict) else None
                if not conversations:
                    conversations = []
                conversation_summary = self._summarize_conversations(conversations) if conversations else ""

                facilitator_input = {
                    "user_id": f"applicant-{job_seeker.id}",
                    "knowledge_base_id": "LK99W8W38P",
                    "questions": questions or [],
                    "job_seeker_data": {
                        "full_name": job_seeker_data.get('full_name') or "",
                        "email": job_seeker_data.get('email') or ""
                    },
                    "job_postings": {
                        "hard_skills": job_posting_skills.get('hard_skills', []) if job_posting_skills else [],
                        "soft_skills": job_posting_skills.get('soft_skills', []) if job_posting_skills else []
                    },
                    "full_text": upload_outputs.get('full_text', conversation_summary) if isinstance(upload_outputs, dict) else conversation_summary,
                    "behavior_text": upload_outputs.get('behavior_text', "") if isinstance(upload_outputs, dict) else "",
                    "big5_text": upload_outputs.get('big5_text', "") if isinstance(upload_outputs, dict) else "",
                    "aiqa_text": upload_outputs.get('aiqa_text', "") if isinstance(upload_outputs, dict) else "",
                    # 호환성 유지 목적의 식별자 전달
                    "job_posting_id": job_posting_id,
                }

                logger.info("➡️ FacilitatorAI 호출")
                async with session.post(FACILITATOR_AI_URL, json=facilitator_input, headers={"Content-Type": "application/json"}) as fac_resp:
                    fac_data = await fac_resp.json()

                if fac_data.get('success', False):
                    evaluation = fac_data.get('evaluation', {}) or {}
                    message_history = fac_data.get('message_history', conversations) or conversations

                    # Normalize evaluation fields and fill missing pieces
                    hard_eval = evaluation.get('hard_eval') or evaluation.get('hard_detail_scores') or evaluation.get('hardEval')
                    soft_eval = evaluation.get('soft_eval') or evaluation.get('soft_detail_scores') or evaluation.get('softEval')

                    if hard_eval is not None and not isinstance(hard_eval, list):
                        try:
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

                    if hard_eval is not None:
                        evaluation['hard_eval'] = hard_eval
                        evaluation['hard_detail_scores'] = hard_eval
                    if soft_eval is not None:
                        evaluation['soft_eval'] = soft_eval
                        evaluation['soft_detail_scores'] = soft_eval

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
                        'evaluation': evaluation,
                        'conversations': message_history
                    }
                else:
                    raise Exception(f"FacilitatorAI 호출 실패: {fac_data}")

        except Exception as e:
            logger.error(f"❌ conduct_interview 오류: {str(e)}")
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

