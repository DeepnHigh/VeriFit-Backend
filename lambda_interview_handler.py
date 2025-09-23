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
    AWS Lambda 함수: 면접 관련 AI 작업 처리
    - 면접 질문 생성
    - 면접 답변 생성  
    - 최종 평가 생성
    """
    try:
        # 입력 데이터 파싱
        if 'body' in event:
            body_data = json.loads(event.get('body', '{}'))
            task_type = body_data.get('task_type', '')
            prompt = body_data.get('prompt', '')
        else:
            task_type = event.get('task_type', '')
            prompt = event.get('prompt', '')
        
        if not task_type or not prompt:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'success': False,
                    'error': 'task_type and prompt are required'
                }, ensure_ascii=False)
            }
        
        logger.info(f"Lambda 시작 - Task: {task_type}, Prompt 길이: {len(prompt)}")
        
        # 모델 ID 설정
        model_id = 'anthropic.claude-3-5-sonnet-20240620-v1:0'
        
        # 작업 유형에 따른 처리
        if task_type == 'generate_interview_questions':
            return handle_question_generation(prompt, model_id)
        elif task_type == 'generate_interview_answer':
            return handle_answer_generation(prompt, model_id)
        elif task_type == 'generate_evaluation':
            return handle_evaluation_generation(prompt, model_id)
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'success': False,
                    'error': f'Unknown task_type: {task_type}'
                }, ensure_ascii=False)
            }
            
    except Exception as e:
        logger.error(f"Lambda 처리 중 오류: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': f'Internal server error: {str(e)}'
            }, ensure_ascii=False)
        }

def handle_question_generation(prompt: str, model_id: str) -> Dict[str, Any]:
    """면접 질문 생성 처리"""
    try:
        # Bedrock API 요청
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2000,
            "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
        }
        
        logger.info(f"면접 질문 생성 요청 시작 - Model: {model_id}")
        
        response = bedrock_client.invoke_model(
            modelId=model_id,
            body=json.dumps(body),
            contentType="application/json"
        )
        
        response_body = json.loads(response['body'].read())
        content = response_body['content'][0]['text']
        
        logger.info(f"면접 질문 생성 응답 수신 - 길이: {len(content)}")
        
        # JSON 파싱 시도
        try:
            questions_data = json.loads(content)
            if isinstance(questions_data, dict) and 'questions' in questions_data:
                questions = questions_data['questions']
            else:
                # JSON 파싱 실패 시 기본 질문 반환
                questions = get_default_questions()
        except json.JSONDecodeError:
            logger.warning("JSON 파싱 실패, 기본 질문 사용")
            questions = get_default_questions()
        
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

def handle_answer_generation(prompt: str, model_id: str) -> Dict[str, Any]:
    """면접 답변 생성 처리"""
    try:
        # Bedrock API 요청
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
        }
        
        logger.info(f"면접 답변 생성 요청 시작 - Model: {model_id}")
        
        response = bedrock_client.invoke_model(
            modelId=model_id,
            body=json.dumps(body),
            contentType="application/json"
        )
        
        response_body = json.loads(response['body'].read())
        content = response_body['content'][0]['text']
        
        logger.info(f"면접 답변 생성 응답 수신 - 길이: {len(content)}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'answer': content.strip(),
                'raw_response': content
            }, ensure_ascii=False)
        }
        
    except Exception as e:
        logger.error(f"면접 답변 생성 중 오류: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': f'Answer generation failed: {str(e)}'
            }, ensure_ascii=False)
        }

def handle_evaluation_generation(prompt: str, model_id: str) -> Dict[str, Any]:
    """최종 평가 생성 처리"""
    try:
        # Bedrock API 요청
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1500,
            "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
        }
        
        logger.info(f"최종 평가 생성 요청 시작 - Model: {model_id}")
        
        response = bedrock_client.invoke_model(
            modelId=model_id,
            body=json.dumps(body),
            contentType="application/json"
        )
        
        response_body = json.loads(response['body'].read())
        content = response_body['content'][0]['text']
        
        logger.info(f"최종 평가 생성 응답 수신 - 길이: {len(content)}")
        
        # JSON 파싱 시도
        try:
            evaluation_data = json.loads(content)
            if isinstance(evaluation_data, dict):
                # 필수 필드 검증 및 기본값 설정
                evaluation_data = validate_evaluation_data(evaluation_data)
            else:
                evaluation_data = get_default_evaluation()
        except json.JSONDecodeError:
            logger.warning("JSON 파싱 실패, 기본 평가 사용")
            evaluation_data = get_default_evaluation()
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'evaluation': evaluation_data,
                'raw_response': content
            }, ensure_ascii=False)
        }
        
    except Exception as e:
        logger.error(f"최종 평가 생성 중 오류: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': f'Evaluation generation failed: {str(e)}'
            }, ensure_ascii=False)
        }

def get_default_questions() -> list:
    """기본 면접 질문 리스트"""
    return [
        "이 포지션에 지원한 이유를 말씀해주세요.",
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

def get_default_evaluation() -> dict:
    """기본 평가 결과 (AI 평가 실패 시 사용)"""
    return {
        'hard_score': 0.0,
        'soft_score': 0.0,
        'total_score': 0.0,
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
