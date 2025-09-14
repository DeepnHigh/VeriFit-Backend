import json
import boto3
import logging
import os
from typing import Dict, Any

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    AWS Lambda 함수: Bedrock을 통한 개인정보 추출
    """
    try:
        # 입력 데이터 파싱
        extracted_text = event.get('extracted_text', '')
        # model_id는 환경 변수에서 가져오므로 event에서 제거
        
        if not extracted_text:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'extracted_text is required'
                })
            }
        
        logger.info(f"Lambda 시작 - 텍스트 길이: {len(extracted_text)}")
        
        # 환경 변수에서 설정 가져오기 (없으면 기본값 사용)
        region = os.environ.get('AWS_REGION', 'us-west-1')
        # 교차 리전 추론이 가능한 Claude 3.5 Sonnet 모델 사용
        model_id = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-5-sonnet-20241022-v2:0')
        
        # Bedrock 클라이언트 초기화
        bedrock_client = boto3.client('bedrock-runtime', region_name=region)
        
        # 프롬프트 생성
        prompt = create_prompt(extracted_text)
        
        # Bedrock API 요청 (Amazon Nova 모델용)
        if model_id.startswith('amazon.nova'):
            body = {
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 1000,
                "temperature": 0.1
            }
        else:
            # Claude 모델용
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
        
        logger.info(f"Bedrock API 요청 시작 - Model: {model_id}, Region: {region}")
        
        response = bedrock_client.invoke_model(
            modelId=model_id,
            body=json.dumps(body),
            contentType="application/json"
        )
        
        logger.info("Bedrock API 응답 수신")
        
        response_body = json.loads(response['body'].read())
        
        # Amazon Nova와 Claude 모델의 응답 형식이 다름
        if model_id.startswith('amazon.nova'):
            content = response_body['output']['message']['content'][0]['text']
        else:
            content = response_body['content'][0]['text']
        
        logger.info(f"LLM 응답 길이: {len(content)}")
        
        # JSON 파싱
        personal_info = parse_response(content)
        
        logger.info("개인정보 추출 완료")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'personal_info': personal_info,
                'raw_response': content
            })
        }
        
    except Exception as e:
        logger.error(f"Lambda 오류: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }

def create_prompt(extracted_text: str) -> str:
    """개인정보 추출을 위한 프롬프트 생성"""
    return f"""
다음 텍스트에서 개인정보를 추출하여 JSON 형식으로 반환해주세요.

텍스트:
{extracted_text}

다음 형식의 JSON으로 응답해주세요:
{{
    "name": "이름 (없으면 null)",
    "phone": "전화번호 (없으면 null)",
    "email": "이메일 (없으면 null)",
    "address": "주소 (없으면 null)",
    "birth_date": "생년월일 (없으면 null)",
    "gender": "성별 (없으면 null)"
}}

주의사항:
- 정확한 정보만 추출하고, 추측하지 마세요
- 전화번호는 숫자와 하이픈만 포함하세요
- 이메일은 @ 기호가 포함된 형태여야 합니다
- 주소는 상세주소까지 포함하세요
- 생년월일은 YYYY-MM-DD 형식으로 변환하세요
- 정보가 없으면 null로 설정하세요
"""

def parse_response(content: str) -> Dict[str, Any]:
    """LLM 응답을 파싱하여 개인정보 추출"""
    try:
        # JSON 부분만 추출
        start_idx = content.find('{')
        end_idx = content.rfind('}') + 1
        
        if start_idx == -1 or end_idx == 0:
            raise ValueError("JSON 형식을 찾을 수 없습니다")
        
        json_str = content[start_idx:end_idx]
        data = json.loads(json_str)
        
        return {
            'name': data.get('name'),
            'phone': data.get('phone'),
            'email': data.get('email'),
            'address': data.get('address'),
            'birth_date': data.get('birth_date'),
            'gender': data.get('gender')
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON 파싱 오류: {str(e)}")
        raise ValueError(f"JSON 파싱 실패: {str(e)}")
    except Exception as e:
        logger.error(f"응답 파싱 오류: {str(e)}")
        raise ValueError(f"응답 파싱 실패: {str(e)}")
