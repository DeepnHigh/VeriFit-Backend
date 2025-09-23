import json
import boto3
import logging
import os
from typing import Dict, Any

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Bedrock 클라이언트 초기화
bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')

def lambda_handler(event, context):
    """
    AWS Lambda 함수: 면접 질문 생성
    - 채용공고 정보를 받아서 면접 질문 10개 생성
    """
    try:
        # 입력 데이터 파싱
        if 'body' in event:
            body_data = json.loads(event.get('body', '{}'))
            job_posting_data = body_data.get('job_posting_data', {})
        else:
            job_posting_data = event.get('job_posting_data', {})
        
        if not job_posting_data:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'success': False,
                    'error': 'job_posting_data is required'
                }, ensure_ascii=False)
            }
        
        logger.info(f"면접 질문 생성 시작 - 공고: {job_posting_data.get('title', 'Unknown')}")
        
        # 모델 ID 설정
        model_id = 'anthropic.claude-3-5-sonnet-20240620-v1:0'
        
        # 질문 생성 프롬프트 생성
        prompt = create_question_generation_prompt(job_posting_data)
        
        # Bedrock API 요청
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2000,
            "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
        }
        
        logger.info(f"Bedrock API 요청 시작 - Model: {model_id}")
        
        response = bedrock_client.invoke_model(
            modelId=model_id,
            body=json.dumps(body),
            contentType="application/json"
        )
        
        logger.info("Bedrock API 응답 수신")
        
        response_body = json.loads(response['body'].read())
        content = response_body['content'][0]['text']
        
        logger.info(f"LLM 응답 길이: {len(content)}")
        
        # JSON 파싱 시도
        try:
            questions_data = json.loads(content)
            if isinstance(questions_data, dict) and 'questions' in questions_data:
                questions = questions_data['questions']
            else:
                # JSON 파싱 실패 시 기본 질문 반환
                questions = get_default_questions(job_posting_data)
        except json.JSONDecodeError:
            logger.warning("JSON 파싱 실패, 기본 질문 사용")
            questions = get_default_questions(job_posting_data)
        
        logger.info(f"✅ 면접 질문 {len(questions)}개 생성 완료")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'questions': questions,
                'raw_response': content
            }, ensure_ascii=False)
        }
        
    except Exception as e:
        logger.error(f"면접 질문 생성 중 오류: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': f'Question generation failed: {str(e)}'
            }, ensure_ascii=False)
        }

def create_question_generation_prompt(job_posting_data: dict) -> str:
    """채용공고 정보를 바탕으로 질문 생성 프롬프트 생성"""
    
    # requirements를 리스트로 변환
    requirements_text = ""
    if job_posting_data.get('requirements'):
        try:
            if isinstance(job_posting_data['requirements'], list):
                requirements_text = "\n".join([f"- {req}" for req in job_posting_data['requirements']])
            else:
                requirements_text = job_posting_data['requirements']
        except Exception:
            requirements_text = str(job_posting_data.get('requirements', ''))
    
    # 하드스킬, 소프트스킬을 문자열로 변환
    hard_skills_text = ", ".join(job_posting_data.get('hard_skills', [])) if job_posting_data.get('hard_skills') else "없음"
    soft_skills_text = ", ".join(job_posting_data.get('soft_skills', [])) if job_posting_data.get('soft_skills') else "없음"
    
    prompt = f"""
다음 채용공고를 바탕으로 면접 질문 10개를 생성해주세요.

=== 채용공고 정보 ===
제목: {job_posting_data.get('title', '')}
직급: {job_posting_data.get('position_level', '')}
고용형태: {job_posting_data.get('employment_type', '')}
위치: {job_posting_data.get('location', '')}
급여: {job_posting_data.get('salary_min', '')}~{job_posting_data.get('salary_max', '')}만원

주요업무:
{job_posting_data.get('main_tasks', '')}

필수요구사항:
{requirements_text}

우대사항:
{job_posting_data.get('preferred', '없음')}

필수 하드스킬: {hard_skills_text}
필수 소프트스킬: {soft_skills_text}

=== 질문 생성 요구사항 ===
1. 기술적 질문 (하드스킬 관련): 3개
2. 경험 기반 질문 (소프트스킬 관련): 3개  
3. 상황 대응 질문: 2개
4. 회사 적합성 질문: 2개

각 질문은 구체적이고 실무에 도움이 되는 내용으로 작성해주세요.
지원자의 실제 경험과 역량을 파악할 수 있는 질문으로 구성해주세요.
채용 공고에 있는 정보만 활용하여 질문을 생성해주세요.

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

def get_default_questions(job_posting_data: dict) -> list:
    """기본 면접 질문 리스트"""
    title = job_posting_data.get('title', '이 포지션')
    return [
        f"{title}에 지원한 이유를 말씀해주세요.",
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
