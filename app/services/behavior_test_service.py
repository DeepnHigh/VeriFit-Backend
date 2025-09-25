from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import uuid
from app.models.job_seeker import JobSeeker
from app.models.behavior_test_result import BehaviorTestResult
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
import json

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

    def save_behavior_result(self, user_id: str, situation_text: str, selected_character: str, conversation_history_json: str) -> Dict[str, Any]:
        """
        행동검사 결과 저장
        - conversation_history_json: JSON 문자열 (메시지 배열)
        """
        try:
            uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        except Exception:
            return {"success": False, "message": "잘못된 user_id 형식"}

        job_seeker = self.db.query(JobSeeker).filter(JobSeeker.user_id == uid).first()
        if not job_seeker:
            return {"success": False, "message": "구직자 정보를 찾을 수 없습니다"}

        # selected_character 검증
        if selected_character not in ["A", "B", "C"]:
            return {"success": False, "message": "selected_character는 'A' | 'B' | 'C' 중 하나여야 합니다"}

        # conversation_history 파싱 및 검증(간단 체크)
        try:
            parsed_history = json.loads(conversation_history_json) if isinstance(conversation_history_json, str) else conversation_history_json
            if not isinstance(parsed_history, list):
                return {"success": False, "message": "conversation_history는 JSON 배열이어야 합니다"}
        except Exception:
            return {"success": False, "message": "conversation_history JSON 파싱 실패"}

        try:
            # 사람이 읽기 쉬운 대화 문자열 생성
            conversation_text_lines = []
            for message in parsed_history:
                try:
                    role = str(message.get("role", "")).strip() or "unknown"
                    content = str(message.get("content", "")).strip()
                    timestamp = str(message.get("timestamp", "")).strip()
                    if timestamp:
                        conversation_text_lines.append(f"[{timestamp}] {role}: {content}")
                    else:
                        conversation_text_lines.append(f"{role}: {content}")
                except Exception:
                    # 안전망: 예상치 못한 항목은 문자열로 덤프
                    conversation_text_lines.append(str(message))

            formatted_behavior_text = (
                f"<상황> : {situation_text or ''}\n"
                f"<선택> : {selected_character}\n"
                f"<대화> : " + ("\n".join(conversation_text_lines) if conversation_text_lines else "")
            )

            # 기존 레코드가 있으면 최신 1건 업데이트, 없으면 생성
            existing_result = (
                self.db.query(BehaviorTestResult)
                .filter(BehaviorTestResult.job_seeker_id == job_seeker.id)
                .order_by(BehaviorTestResult.test_date.desc())
                .first()
            )

            if existing_result:
                existing_result.situation_text = situation_text or ""
                existing_result.selected_character = selected_character
                existing_result.conversation_history = parsed_history
                existing_result.test_date = func.now()
                result = existing_result
            else:
                result = BehaviorTestResult(
                    job_seeker_id=job_seeker.id,
                    situation_text=situation_text or "",
                    selected_character=selected_character,
                    conversation_history=parsed_history
                )
                self.db.add(result)
            # job_seekers.behavior_text에도 저장(덮어쓰기)
            job_seeker.behavior_text = formatted_behavior_text
            self.db.add(job_seeker)
            self.db.commit()
            self.db.refresh(result)
            return {
                "success": True,
                "id": str(result.id),
                "test_date": result.test_date.isoformat() if result.test_date else None
            }
        except Exception as e:
            self.db.rollback()
            return {"success": False, "message": f"저장 실패: {str(e)}"}
