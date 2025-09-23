from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.job_posting import JobPosting
from app.services.lambda_bedrock_service import LambdaBedrockService
import json
import logging

logger = logging.getLogger(__name__)

class InterviewQuestionService:
    """면접 질문 생성 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
        self.bedrock_service = LambdaBedrockService()
    
    async def generate_interview_questions(self, job_posting: JobPosting) -> List[str]:
        """
        채용공고 기반 면접 질문 리스트 생성 (DB 저장)
        
        Args:
            job_posting: JobPosting 모델 객체
            
        Returns:
            List[str]: 생성된 면접 질문 리스트
        """
        try:
            # 1. 기존 질문이 있는지 확인 (DB에서 조회)
            if job_posting.interview_questions:
                existing_questions = job_posting.interview_questions
                logger.info(f"✅ 저장된 면접 질문 {len(existing_questions)}개 사용")
                return existing_questions
            
            # 2. 새 질문 생성
            job_posting_data = self._convert_job_posting_to_dict(job_posting)
            response = await self.bedrock_service.generate_interview_questions(job_posting_data)
            questions = self._parse_questions_response(response)
            
            # 3. 생성된 질문을 DB에 저장
            job_posting.interview_questions = questions
            self.db.commit()
            self.db.refresh(job_posting)
            
            logger.info(f"✅ 면접 질문 {len(questions)}개 생성 및 DB 저장 완료")
            return questions
            
        except Exception as e:
            logger.error(f"❌ 면접 질문 생성 중 오류: {str(e)}")
            # 기본 질문 리스트 반환
            return self._get_default_questions(job_posting)
    
    
    def _convert_job_posting_to_dict(self, job_posting: JobPosting) -> Dict[str, Any]:
        """JobPosting 모델을 딕셔너리로 변환"""
        # requirements를 리스트로 변환
        requirements_list = []
        if job_posting.requirements:
            try:
                if isinstance(job_posting.requirements, str):
                    requirements_list = json.loads(job_posting.requirements)
                    if not isinstance(requirements_list, list):
                        requirements_list = [job_posting.requirements]
                else:
                    requirements_list = [job_posting.requirements]
            except json.JSONDecodeError:
                requirements_list = [job_posting.requirements]
        
        return {
            'title': job_posting.title,
            'position_level': job_posting.position_level,
            'employment_type': job_posting.employment_type,
            'location': job_posting.location,
            'salary_min': job_posting.salary_min,
            'salary_max': job_posting.salary_max,
            'main_tasks': job_posting.main_tasks,
            'requirements': requirements_list,
            'preferred': job_posting.preferred,
            'hard_skills': job_posting.hard_skills or [],
            'soft_skills': job_posting.soft_skills or []
        }
    
    def _create_question_generation_prompt(self, job_posting: JobPosting) -> str:
        """채용공고 정보를 바탕으로 질문 생성 프롬프트 생성"""
        
        # requirements를 리스트로 변환
        requirements_text = ""
        if job_posting.requirements:
            try:
                if isinstance(job_posting.requirements, str):
                    requirements_list = json.loads(job_posting.requirements)
                    if isinstance(requirements_list, list):
                        requirements_text = "\n".join([f"- {req}" for req in requirements_list])
                    else:
                        requirements_text = job_posting.requirements
                else:
                    requirements_text = str(job_posting.requirements)
            except json.JSONDecodeError:
                requirements_text = job_posting.requirements
        
        # 하드스킬, 소프트스킬을 문자열로 변환
        hard_skills_text = ", ".join(job_posting.hard_skills) if job_posting.hard_skills else "없음"
        soft_skills_text = ", ".join(job_posting.soft_skills) if job_posting.soft_skills else "없음"
        
        prompt = f"""
다음 채용공고를 바탕으로 면접 질문 10개를 생성해주세요.

=== 채용공고 정보 ===
제목: {job_posting.title}
직급: {job_posting.position_level}
고용형태: {job_posting.employment_type}
위치: {job_posting.location}
급여: {job_posting.salary_min}~{job_posting.salary_max}만원

주요업무:
{job_posting.main_tasks}

필수요구사항:
{requirements_text}

우대사항:
{job_posting.preferred or "없음"}

필수 하드스킬: {hard_skills_text}
필수 소프트스킬: {soft_skills_text}

=== 질문 생성 요구사항 ===
1. 기술적 질문 (하드스킬 관련): 3개
2. 경험 기반 질문 (소프트스킬 관련): 3개  
3. 상황 대응 질문: 2개
4. 회사 적합성 질문: 2개

각 질문은 구체적이고 실무에 도움이 되는 내용으로 작성해주세요.
지원자의 실제 경험과 역량을 파악할 수 있는 질문으로 구성해주세요.

응답 형식:
{{
    "questions": [
        "질문1",
        "질문2",
        "질문3",
        "질문4",
        "질문5",
        "질문6",
        "질문7",
        "질문8",
        "질문9",
        "질문10"
    ]
}}
"""
        return prompt
    
    def _parse_questions_response(self, response: Dict[str, Any]) -> List[str]:
        """Lambda 응답에서 질문 리스트 파싱"""
        try:
            if response.get('success', False):
                # Lambda에서 반환된 질문 리스트 파싱
                questions_data = response.get('questions', [])
                if isinstance(questions_data, list):
                    return questions_data
                
                # JSON 문자열인 경우 파싱
                if isinstance(questions_data, str):
                    parsed = json.loads(questions_data)
                    if isinstance(parsed, dict) and 'questions' in parsed:
                        return parsed['questions']
                    elif isinstance(parsed, list):
                        return parsed
            
            # 응답 파싱 실패 시 빈 리스트 반환
            logger.warning("질문 응답 파싱 실패, 기본 질문 사용")
            return []
            
        except Exception as e:
            logger.error(f"질문 응답 파싱 중 오류: {str(e)}")
            return []
    
    def _get_default_questions(self, job_posting: JobPosting) -> List[str]:
        """기본 면접 질문 리스트 반환 (Lambda 실패 시 사용)"""
        return [
            f"{job_posting.title} 포지션에 지원한 이유를 말씀해주세요.",
            "이전 경험 중 가장 도전적이었던 프로젝트는 무엇인가요?",
            "팀워크가 중요한 상황에서 어떻게 협업하시나요?",
            "새로운 기술을 학습할 때 어떤 방법을 사용하시나요?",
            "업무 중 예상치 못한 문제가 발생했을 때 어떻게 대응하시나요?",
            "이 회사에서 어떤 기여를 하고 싶으신가요?",
            "장기적인 커리어 목표는 무엇인가요?",
            "스트레스 상황에서 어떻게 극복하시나요?",
            "리더십 경험이 있다면 어떤 방식으로 팀을 이끌었나요?",
            "마지막으로 하고 싶은 말씀이 있으시나요?"
        ]
