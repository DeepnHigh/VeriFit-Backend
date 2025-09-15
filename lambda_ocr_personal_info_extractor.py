import json
import boto3
import logging
import os
from typing import Dict, Any

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Bedrock 클라이언트를 모델이 실제로 있는 'us-east-1' 리전으로 생성합니다.
bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')

def lambda_handler(event, context):
    """
    AWS Lambda 함수: OCR에서 추출된 텍스트로부터 개인정보 추출
    """
    try:
        # 입력 데이터 파싱 - API Gateway를 통한 요청과 직접 호출 모두 지원
        if 'body' in event:
            body_data = json.loads(event.get('body', '{}'))
            extracted_text = body_data.get('extracted_text', '')
            image_url = body_data.get('image_url', '')
            document_type = body_data.get('document_type', 'general')
        else:
            extracted_text = event.get('extracted_text', '')
            image_url = event.get('image_url', '')
            document_type = event.get('document_type', 'general')
        
        if not extracted_text:
            return {
                'statusCode': 400, 
                'body': json.dumps({
                    'error': 'extracted_text is required'
                }, ensure_ascii=False)
            }
        
        logger.info(f"OCR 텍스트 처리 시작 - 텍스트 길이: {len(extracted_text)}, 문서 타입: {document_type}")
        
        # 표준 모델 ID를 사용합니다.
        model_id = 'anthropic.claude-3-5-sonnet-20240620-v1:0'
        
        # 문서 타입에 따른 프롬프트 생성
        prompt = create_prompt(extracted_text, document_type, image_url)
        
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1500,  # OCR 텍스트가 길 수 있으므로 토큰 수 증가
            "messages": [{ "role": "user", "content": [{"type": "text", "text": prompt}] }]
        }
        
        logger.info(f"Bedrock API 요청 시작 - Model: {model_id}, Region: us-east-1")
        
        response = bedrock_client.invoke_model(
            modelId=model_id,
            body=json.dumps(body),
            contentType="application/json"
        )
        
        logger.info("Bedrock API 응답 수신")
        
        response_body = json.loads(response['body'].read())
        content = response_body['content'][0]['text']
        
        personal_info = parse_response(content)
        
        logger.info("개인정보 추출 완료")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'personal_info': personal_info,
                'raw_response': content,
                'document_type': document_type,
                'image_url': image_url
            }, ensure_ascii=False)
        }
        
    except Exception as e:
        logger.error(f"Lambda 오류: {str(e)}")
        return {
            'statusCode': 500, 
            'body': json.dumps({
                'success': False, 
                'error': str(e)
            }, ensure_ascii=False)
        }

def create_prompt(extracted_text: str, document_type: str = 'general', image_url: str = '') -> str:
    """
    문서 타입에 따른 개인정보 추출 프롬프트 생성
    """
    base_prompt = f"""다음은 OCR로 추출된 텍스트입니다. 이 텍스트에서 개인정보를 추출하여 JSON 형식으로만 반환해주세요. 다른 설명은 붙이지 마세요.

문서 타입: {document_type}
추출된 텍스트:
{extracted_text}

다음 형식의 JSON으로 응답해주세요:
{{
    "name": "이름 (없으면 null)",
    "phone": "전화번호 (없으면 null)",
    "email": "이메일 (없으면 null)",
    "address": "주소 (없으면 null)",
    "birth_date": "생년월일 (없으면 null)",
    "gender": "성별 (없으면 null)",
    "id_number": "주민등록번호 또는 신분증번호 (없으면 null)",
    "document_type": "{document_type}"
}}"""

    # 문서 타입별 특화 프롬프트
    if document_type == 'id_card':
        base_prompt += """

주민등록증 특화 지침:
- 주민등록번호는 13자리 숫자로 추출하세요
- 성별은 주민등록번호 뒷자리 첫 번째 숫자로 판단하세요 (1,3: 남성, 2,4: 여성)
- 주소는 등록기준지 주소를 우선으로 하세요"""
    
    elif document_type == 'driver_license':
        base_prompt += """

운전면허증 특화 지침:
- 면허번호를 id_number 필드에 추출하세요
- 생년월일은 면허번호에서 추출하거나 별도로 표시된 생년월일을 사용하세요"""
    
    elif document_type == 'passport':
        base_prompt += """

여권 특화 지침:
- 여권번호를 id_number 필드에 추출하세요
- 생년월일은 YYYY-MM-DD 형식으로 변환하세요"""
    
    elif document_type == 'business_card':
        base_prompt += """

명함 특화 지침:
- 회사명, 직책, 부서명 등은 address 필드에 포함하세요
- 이메일과 전화번호를 우선적으로 추출하세요"""
    
    return base_prompt

def parse_response(content: str) -> Dict[str, Any]:
    """
    LLM 응답을 파싱하여 개인정보 추출
    """
    try:
        start_idx = content.find('{')
        end_idx = content.rfind('}') + 1
        
        if start_idx == -1 or end_idx == 0:
            raise ValueError("JSON 형식을 찾을 수 없습니다")
        
        json_str = content[start_idx:end_idx]
        data = json.loads(json_str)
        
        # 기본 필드들 검증 및 정리
        personal_info = {
            'name': data.get('name'),
            'phone': data.get('phone'),
            'email': data.get('email'),
            'address': data.get('address'),
            'birth_date': data.get('birth_date'),
            'gender': data.get('gender'),
            'id_number': data.get('id_number'),
            'document_type': data.get('document_type', 'general')
        }
        
        # 전화번호 정리 (숫자와 하이픈만 남기기)
        if personal_info['phone']:
            phone_cleaned = ''.join(c for c in personal_info['phone'] if c.isdigit() or c == '-')
            if len(phone_cleaned.replace('-', '')) >= 10:  # 최소 10자리
                personal_info['phone'] = phone_cleaned
        
        # 이메일 검증
        if personal_info['email'] and '@' not in personal_info['email']:
            personal_info['email'] = None
        
        return personal_info
        
    except Exception as e:
        logger.error(f"응답 파싱 오류: {str(e)}")
        raise ValueError(f"응답 파싱 실패: {str(e)}")
