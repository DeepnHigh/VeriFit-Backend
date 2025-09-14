import boto3
import json
import logging
import requests
from typing import Dict, Any, Optional
from app.core.config import settings
from app.schemas.personal_info import PersonalInfo

logger = logging.getLogger(__name__)

class BedrockService:
    """AWS Bedrock을 사용한 LLM 서비스"""
    
    def __init__(self):
        self.region = settings.aws_region
        self.model_id = settings.bedrock_model_id
        self.bearer_token = settings.aws_bearer_token_bedrock
        
        logger.info(f"🔧 Bedrock Service 초기화 - Region: {self.region}")
        logger.info(f"🔧 Bedrock Service 초기화 - Model ID: {self.model_id}")
        logger.info(f"🔧 Bedrock Service 초기화 - Bearer Token: {self.bearer_token[:20]}..." if self.bearer_token else "Bearer Token 없음")
        
        # Bearer Token을 환경 변수로 설정
        if self.bearer_token:
            import os
            os.environ['AWS_BEARER_TOKEN_BEDROCK'] = self.bearer_token
            logger.info("✅ Bearer Token 환경 변수 설정 완료")
            self.bedrock_client = None  # Bearer Token 사용 시 boto3 클라이언트 사용 안함
        else:
            # 일반적인 AWS 자격 증명 사용
            self.bedrock_client = boto3.client(
                'bedrock-runtime',
                region_name=self.region
            )
        logger.info("✅ Bedrock 클라이언트 초기화 완료")
    
    async def extract_personal_info(self, extracted_text: str) -> PersonalInfo:
        """추출된 텍스트에서 개인정보 파싱"""
        logger.info(f"🤖 LLM 개인정보 추출 시작")
        logger.info(f"📝 입력 텍스트 길이: {len(extracted_text)} 문자")
        logger.info(f"📝 입력 텍스트 미리보기 (처음 300자): {extracted_text[:300]}...")
        
        try:
            prompt = self._create_prompt(extracted_text)
            logger.info(f"📋 생성된 프롬프트 길이: {len(prompt)} 문자")
            logger.info(f"📋 프롬프트 미리보기 (처음 200자): {prompt[:200]}...")
            
            # Claude 모델용 요청 형식
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
            
            logger.info(f"🚀 Bedrock API 요청 시작...")
            logger.info(f"🔧 요청 설정 - Model: {self.model_id}, Max Tokens: 1000")
            
            if self.bearer_token:
                # Bearer Token을 사용한 직접 HTTP 요청
                url = f"https://bedrock-runtime.{self.region}.amazonaws.com/model/{self.model_id}/invoke"
                headers = {
                    "Authorization": f"Bearer {self.bearer_token}",
                    "Content-Type": "application/json"
                }
                
                logger.info(f"🌐 HTTP 요청 URL: {url}")
                response = requests.post(url, headers=headers, json=body, timeout=60)
                response.raise_for_status()
                
                logger.info(f"✅ Bedrock API 응답 수신")
                response_body = response.json()
                logger.info(f"📊 응답 데이터 키: {list(response_body.keys())}")
                
                content = response_body['content'][0]['text']
                logger.info(f"📝 LLM 응답 길이: {len(content)} 문자")
                logger.info(f"📝 LLM 응답 내용: {content}")
            else:
                # 기존 boto3 클라이언트 사용
                response = self.bedrock_client.invoke_model(
                    modelId=self.model_id,
                    body=json.dumps(body),
                    contentType="application/json"
                )
                
                logger.info(f"✅ Bedrock API 응답 수신")
                response_body = json.loads(response['body'].read())
                logger.info(f"📊 응답 데이터 키: {list(response_body.keys())}")
                
                content = response_body['content'][0]['text']
                logger.info(f"📝 LLM 응답 길이: {len(content)} 문자")
                logger.info(f"📝 LLM 응답 내용: {content}")
            
            # JSON 파싱
            logger.info(f"🔍 JSON 파싱 시작...")
            personal_info = self._parse_response(content)
            logger.info(f"✅ JSON 파싱 성공")
            logger.info(f"📊 추출된 개인정보: {personal_info}")
            logger.info(f"🎉 개인정보 추출 완료: {personal_info}")
            return personal_info
            
        except Exception as e:
            logger.error(f"❌ Error extracting personal info: {str(e)}")
            # AWS 자격 증명 오류인 경우 빈 PersonalInfo 반환
            if "Unable to locate credentials" in str(e):
                logger.error(f"❌ AWS 자격 증명이 설정되지 않았습니다. AWS CLI 설정을 확인하세요.")
                return PersonalInfo()
            raise
    
    def _create_prompt(self, text: str) -> str:
        """개인정보 추출을 위한 프롬프트 생성"""
        return f"""
다음 텍스트에서 개인정보를 추출해주세요. JSON 형식으로 응답해주세요.

추출할 정보:
- email: 이메일 주소
- phone: 전화번호
- education_level: 최종학력 (고졸, 대졸, 석사, 박사 등)
- university: 대학교명
- major: 전공
- graduation_year: 졸업년도
- total_experience_years: 총 경력 년수 (숫자만)
- company_name: 최근 직장명

텍스트:
{text[:5000]}  # 텍스트가 너무 길면 처음 5000자만 사용

응답 형식 (JSON만 반환):
{{
    "email": "이메일주소",
    "phone": "전화번호",
    "education_level": "최종학력",
    "university": "대학교명",
    "major": "전공",
    "graduation_year": "졸업년도",
    "total_experience_years": 경력년수,
    "company_name": "회사명"
}}

정보가 없으면 null로 표시해주세요.
"""
    
    def _parse_response(self, content: str) -> PersonalInfo:
        """Bedrock 응답을 PersonalInfo 객체로 파싱"""
        try:
            # JSON 부분만 추출
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                logger.warning("No JSON found in response")
                return PersonalInfo()
            
            json_str = content[start_idx:end_idx]
            data = json.loads(json_str)
            
            return PersonalInfo(
                email=data.get('email'),
                phone=data.get('phone'),
                education_level=data.get('education_level'),
                university=data.get('university'),
                major=data.get('major'),
                graduation_year=data.get('graduation_year'),
                total_experience_years=data.get('total_experience_years'),
                company_name=data.get('company_name')
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {str(e)}")
            return PersonalInfo()
        except Exception as e:
            logger.error(f"Response parsing failed: {str(e)}")
            return PersonalInfo()
