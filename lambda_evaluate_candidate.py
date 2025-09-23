import json
import boto3
import logging
import os
from typing import Dict, Any
import re

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Bedrock 클라이언트 초기화
bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')

def lambda_handler(event, context):
    """
    AWS Lambda 함수: 지원자 평가
    - 질문과 지원자 정보를 받아서 면접 답변 생성 및 최종 평가
    """
    try:
        # 입력 데이터 파싱
        if 'body' in event:
            body_data = json.loads(event.get('body', '{}'))
            questions = body_data.get('questions', [])
            job_seeker_data = body_data.get('job_seeker_data', {})
            job_posting_skills = body_data.get('job_posting_skills', {})
            applicant_id = body_data.get('applicant_id')
            job_posting_id = body_data.get('job_posting_id')
            kb_id = body_data.get('kb_id')
        else:
            questions = event.get('questions', [])
            job_seeker_data = event.get('job_seeker_data', {})
            job_posting_skills = event.get('job_posting_skills', {})
            applicant_id = event.get('applicant_id')
            job_posting_id = event.get('job_posting_id')
            kb_id = event.get('kb_id')
        
        if not questions or not job_seeker_data:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'success': False,
                    'error': 'questions and job_seeker_data are required'
                }, ensure_ascii=False)
            }
        
        logger.info(f"지원자 평가 시작 - 지원자: {job_seeker_data.get('full_name', 'Unknown')}")
        
        # 모델 ID 설정
        model_id = 'anthropic.claude-3-5-sonnet-20240620-v1:0'
        
        # 면접 대화 진행
        conversations = []
        for i, question in enumerate(questions, 1):
            logger.info(f"질문 {i}/{len(questions)} 처리 중")
            
            # 답변 생성 (KB 참조 포함)
            answer = generate_answer(question, job_seeker_data, model_id, applicant_id, job_posting_id)
            
            conversations.append({
                "question_number": i,
                "question": question,
                "answer": answer,
                "status": "complete",
                "attempts": 1
            })
        
        # 최종 평가 생성
        evaluation_result = generate_final_evaluation(
            conversations, job_posting_skills, model_id
        )
        
        logger.info("✅ 지원자 평가 완료")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'evaluation': evaluation_result,
                'conversations': conversations
            }, ensure_ascii=False)
        }
        
    except Exception as e:
        logger.error(f"지원자 평가 중 오류: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': f'Candidate evaluation failed: {str(e)}'
            }, ensure_ascii=False)
        }

def generate_answer(question: str, job_seeker_data: dict, model_id: str, applicant_id: str = None, job_posting_id: str = None) -> str:
    """지원자 AI를 통해 답변 생성 (KB 참조 포함)"""
    
    # 지원자 RAG 생성
    job_seeker_rag = create_job_seeker_rag(job_seeker_data)
    
    # KB 참조 힌트 생성
    kb_hint = ""
    if applicant_id and job_posting_id:
        kb_hint = f"""
KB scope: s3 key prefix kb/{job_posting_id}/{applicant_id} (aiqa_text/full_text/behavior_text/big5_text)
위 KB에서 지원자의 상세 정보(이력서, AI Q&A, 성격검사, 행동검사)를 참조하여 답변하세요.
"""
    
    prompt = f"""
당신은 {job_seeker_rag}의 정보를 바탕으로 면접에 응답하는 지원자입니다.
{kb_hint}
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
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
        }
        
        response = bedrock_client.invoke_model(
            modelId=model_id,
            body=json.dumps(body),
            contentType="application/json"
        )
        
        response_body = json.loads(response['body'].read())
        content = response_body['content'][0]['text']
        
        return content.strip()
        
    except Exception as e:
        logger.error(f"답변 생성 중 오류: {str(e)}")
        return "답변 생성에 실패했습니다."

def create_job_seeker_rag(job_seeker_data: dict) -> str:
    """지원자 이력서 RAG 생성"""
    try:
        rag_content = f"""
=== 지원자 기본 정보 ===
이름: {job_seeker_data.get('full_name', '정보 없음')}
이메일: {job_seeker_data.get('email', '정보 없음')}
전화번호: {job_seeker_data.get('phone', '정보 없음')}
위치: {job_seeker_data.get('location', '정보 없음')}

=== 경력 정보 ===
총 경력: {job_seeker_data.get('total_experience_years', 0)}년
최근 직장: {job_seeker_data.get('company_name', '정보 없음')}

=== 학력 정보 ===
학력: {job_seeker_data.get('education_level', '정보 없음')}
대학교: {job_seeker_data.get('university', '정보 없음')}
전공: {job_seeker_data.get('major', '정보 없음')}
졸업년도: {job_seeker_data.get('graduation_year', '정보 없음')}

=== 자기소개 ===
{job_seeker_data.get('bio', '자기소개 없음')}

=== 포트폴리오 ===
{format_json_field(job_seeker_data.get('portfolios', []), '포트폴리오')}

=== 이력서 ===
{format_json_field(job_seeker_data.get('resumes', []), '이력서')}

=== GitHub 레포지토리 ===
{format_json_field(job_seeker_data.get('github_repositories', []), 'GitHub')}

=== 자격증 ===
{format_json_field(job_seeker_data.get('certificates', []), '자격증')}
"""
        
        return rag_content
        
    except Exception as e:
        logger.error(f"지원자 RAG 생성 중 오류: {str(e)}")
        return f"지원자 정보: {job_seeker_data.get('full_name', '정보 없음')}"

def format_json_field(data, field_name: str) -> str:
    """JSON 필드를 문자열로 포맷팅"""
    if not data:
        return f"{field_name} 없음"
    
    try:
        if isinstance(data, list):
            return "\n".join([f"- {item}" for item in data])
        else:
            return f"{field_name}: {data}"
    except Exception:
        return f"{field_name} 정보 파싱 오류"

def generate_final_evaluation(conversations: list, job_posting_skills: dict, model_id: str) -> dict:
    """면접 대화를 바탕으로 최종 평가 결과 생성"""
    try:
        # 대화 내용 요약
        conversation_summary = summarize_conversations(conversations)
        
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

JSON 형태로, 오직 하나의 JSON 객체만, 추가 설명/마크다운/코드블록 없이 출력하세요:
{{
    "hard_score": 점수(0-100),
    "soft_score": 점수(0-100),
    "total_score": 점수(0-100),
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
        
        # Bedrock API 요청
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1500,
            "messages": [{"role": "user", "content": [{"type": "text", "text": evaluation_prompt}]}]
        }
        
        response = bedrock_client.invoke_model(
            modelId=model_id,
            body=json.dumps(body),
            contentType="application/json"
        )
        
        response_body = json.loads(response['body'].read())
        content = response_body['content'][0]['text']
        
        # JSON 파싱 시도 (강화)
        try:
            evaluation_data = _extract_json_object(content)
            if not evaluation_data:
                raise json.JSONDecodeError("no-json", content, 0)
            if isinstance(evaluation_data, dict):
                evaluation_data = validate_evaluation_data(evaluation_data)
            else:
                evaluation_data = get_default_evaluation(conversations)
        except json.JSONDecodeError:
            logger.warning("JSON 파싱 실패(강화 파서), 기본 평가 사용. content snippet: %s", content[:200])
            evaluation_data = get_default_evaluation(conversations)

        return evaluation_data
        
    except Exception as e:
        logger.error(f"최종 평가 생성 중 오류: {str(e)}")
        return get_default_evaluation(conversations)

def summarize_conversations(conversations: list) -> str:
    """대화 내용 요약"""
    summary = "=== 면접 대화 요약 ===\n"
    
    for conv in conversations:
        summary += f"\n질문 {conv['question_number']}: {conv['question']}\n"
        summary += f"답변: {conv['answer'][:200]}...\n"
        summary += f"상태: {conv['status']} (시도 {conv['attempts']}회)\n"
    
    return summary

def validate_evaluation_data(evaluation_data: dict) -> dict:
    """평가 데이터 검증 및 기본값 설정"""
    # 점수 필드에 대해서는 0점을 기본값으로 설정 (하드코딩 방지)
    score_fields = {
        'hard_score': 0.0,
        'soft_score': 0.0,
        'total_score': 0.0
    }
    
    # 텍스트 필드에 대해서는 기본 메시지 설정
    text_fields = {
        'ai_summary': 'AI 평가가 완료되지 않았습니다.',
        'strengths_content': '평가 데이터가 부족합니다.',
        'strengths_opinion': '추가 평가가 필요합니다.',
        'strengths_evidence': '평가 데이터가 부족합니다.',
        'concerns_content': '평가 데이터가 부족합니다.',
        'concerns_opinion': '추가 평가가 필요합니다.',
        'concerns_evidence': '평가 데이터가 부족합니다.',
        'followup_content': '추가 평가가 필요합니다.',
        'followup_opinion': '추가 평가가 필요합니다.',
        'followup_evidence': '평가 데이터가 부족합니다.',
        'final_opinion': 'AI 평가를 완료할 수 없었습니다.'
    }
    
    # 점수 필드 검증 및 설정
    for field, default_value in score_fields.items():
        if field not in evaluation_data:
            evaluation_data[field] = default_value
        else:
            # 점수 범위 검증 (0-100)
            score = evaluation_data[field]
            if not isinstance(score, (int, float)) or score < 0 or score > 100:
                evaluation_data[field] = default_value
    
    # 텍스트 필드 검증 및 설정
    for field, default_value in text_fields.items():
        if field not in evaluation_data or not evaluation_data[field]:
            evaluation_data[field] = default_value
    
    return evaluation_data

def get_default_evaluation(conversations: list) -> dict:
    """기본 평가 결과 (AI 평가 실패 시 사용)"""
    complete_answers = sum(1 for conv in conversations if conv['status'] == 'complete')
    total_questions = len(conversations)
    completion_rate = (complete_answers / total_questions) * 100 if total_questions > 0 else 0
    
    # 완료율에 따른 동적 점수 계산
    base_score = min(completion_rate * 0.8, 85.0)  # 완료율의 80%를 점수로, 최대 85점
    
    return {
        'hard_score': base_score,
        'soft_score': base_score,
        'total_score': base_score,
        'ai_summary': f'면접 완료율 {completion_rate:.1f}%로 기본적인 평가가 완료되었습니다. (AI 평가 실패로 기본 점수 적용)',
        'strengths_content': '면접에 성실히 응답했습니다.',
        'strengths_opinion': '기본적인 소통 능력을 보여주었습니다.',
        'strengths_evidence': '면접 질문에 대해 성실하게 답변했습니다.',
        'concerns_content': '더 구체적인 경험과 역량 확인이 필요합니다.',
        'concerns_opinion': '추가적인 기술적 검증이 필요할 수 있습니다.',
        'concerns_evidence': '일부 질문에 대한 답변이 불완전하거나 구체적이지 않았습니다.',
        'followup_content': '추가 면접이나 기술 테스트를 통한 검증이 필요합니다.',
        'followup_opinion': '더 정확한 평가를 위해 추가 검증이 권장됩니다.',
        'followup_evidence': '현재 면접 결과만으로는 정확한 역량 평가가 어렵습니다.',
        'final_opinion': '기본적인 자격은 갖추었으나, 추가 검증이 필요합니다.'
    }

def _extract_json_object(text: str) -> dict:
    """Extract the first top-level JSON object from text and parse it.
    Falls back to {} if parsing fails."""
    if not isinstance(text, str):
        return {}
    # Heuristic: find first '{' and last '}' and attempt to parse
    try:
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            candidate = text[start:end+1]
            return json.loads(candidate)
    except Exception:
        pass
    return {}
