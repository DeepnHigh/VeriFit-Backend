import boto3
import json
import logging
from typing import Dict, Any, Optional
from app.core.config import settings
from app.schemas.personal_info import PersonalInfo
import urllib.request
import urllib.error
import botocore
from botocore.session import get_session
from botocore.auth import SigV4Auth
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class LambdaBedrockService:
    """AWS Lambda를 통한 Bedrock LLM 서비스"""
    
    def __init__(self):
        self.region = settings.aws_region
        self.model_id = settings.bedrock_model_id
        self.lambda_function_name = getattr(settings, 'lambda_function_name', 'verifit-bedrock-extractor')
        
        logger.info(f"🔧 Lambda Bedrock Service 초기화 - Region: {self.region}")
        logger.info(f"🔧 Lambda Bedrock Service 초기화 - Model ID: {self.model_id}")
        logger.info(f"🔧 Lambda Bedrock Service 초기화 - Function: {self.lambda_function_name}")
        
        # Lambda Function URL이 있으면 HTTP 경로 우선 사용
        self.lambda_function_url: Optional[str] = getattr(settings, 'lambda_function_url', None)
        self.lambda_function_url_auth: Optional[str] = getattr(settings, 'lambda_function_url_auth', 'NONE')
        if self.lambda_function_url:
            logger.info(f"🌐 Lambda Function URL 사용: {self.lambda_function_url}")
            self.lambda_client = None
        else:
            # Lambda 클라이언트 초기화 (AWS 자격 증명 필요)
            self.lambda_client = boto3.client('lambda', region_name=self.region)
            logger.info("✅ Lambda 클라이언트 초기화 완료")
    
    async def extract_personal_info(self, extracted_text: str) -> PersonalInfo:
        """Lambda를 통해 개인정보 추출"""
        logger.info(f"🤖 Lambda Bedrock 개인정보 추출 시작")
        logger.info(f"📝 입력 텍스트 길이: {len(extracted_text)} 문자")
        logger.info(f"📝 입력 텍스트 미리보기 (처음 300자): {extracted_text[:300]}...")
        
        try:
            # Lambda 함수 호출을 위한 페이로드 생성
            payload = {
                'extracted_text': extracted_text,
                'model_id': self.model_id
            }
            
            logger.info(f"🚀 Lambda 호출 시작...")
            
            # 1) Function URL 경로
            if self.lambda_function_url:
                try:
                    url = self.lambda_function_url
                    data_bytes = json.dumps(payload).encode('utf-8')
                    headers = {'Content-Type': 'application/json'}

                    # AWS_IAM 일 경우 SigV4 서명 추가
                    if (self.lambda_function_url_auth or '').upper() == 'AWS_IAM':
                        parsed = urlparse(url)
                        request = botocore.awsrequest.AWSRequest(
                            method='POST', url=url, data=data_bytes, headers=headers
                        )
                        session = get_session()
                        creds = session.get_credentials()
                        SigV4Auth(creds, 'lambda', parsed.hostname.split('.')[2]).add_auth(request)
                        signed_headers = dict(request.headers.items())
                        headers.update(signed_headers)

                    req = urllib.request.Request(url, data=data_bytes, headers=headers, method='POST')
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        resp_text = resp.read().decode('utf-8')
                        response_payload = json.loads(resp_text)
                except urllib.error.HTTPError as e:
                    err_body = e.read().decode('utf-8') if e.fp else ''
                    logger.error(f"❌ Function URL HTTPError: {e.code} {err_body}")
                    raise Exception(f"Function URL 호출 실패: {e.code} {err_body}")
                except urllib.error.URLError as e:
                    logger.error(f"❌ Function URL URLError: {e.reason}")
                    raise Exception(f"Function URL 호출 실패: {e.reason}")
            else:
                # 2) boto3 Lambda Invoke 경로
                logger.info(f"🔧 Lambda 함수: {self.lambda_function_name}")
                response = self.lambda_client.invoke(
                    FunctionName=self.lambda_function_name,
                    InvocationType='RequestResponse',  # 동기 호출
                    Payload=json.dumps(payload)
                )
                logger.info(f"✅ Lambda 함수 응답 수신")
                response_payload = json.loads(response['Payload'].read())
            
            # Function URL의 경우 StatusCode가 없으므로 payload 기반 판정
            if not response_payload.get('success', False) and response_payload.get('statusCode') not in (200, None):
                logger.error(f"❌ Lambda 호출 오류: {response_payload}")
                raise Exception(f"Lambda 실행 실패: {response_payload}")
            
            if not response_payload.get('success', False):
                logger.error(f"❌ Lambda 처리 실패: {response_payload}")
                raise Exception(f"Lambda 처리 실패: {response_payload.get('error', 'Unknown error')}")
            
            # 개인정보 데이터 추출
            personal_info_data = response_payload.get('personal_info', {})
            raw_response = response_payload.get('raw_response', '')
            
            logger.info(f"📊 Lambda 응답 데이터 키: {list(personal_info_data.keys())}")
            logger.info(f"📝 LLM 원본 응답: {raw_response}")
            
            # PersonalInfo 객체 생성
            personal_info = PersonalInfo(
                name=personal_info_data.get('name'),
                phone=personal_info_data.get('phone'),
                email=personal_info_data.get('email'),
                address=personal_info_data.get('address'),
                birth_date=personal_info_data.get('birth_date'),
                gender=personal_info_data.get('gender')
            )
            
            logger.info(f"✅ Lambda Bedrock 개인정보 추출 완료")
            logger.info(f"📊 추출 결과: {personal_info}")
            
            return personal_info
            
        except Exception as e:
            logger.error(f"❌ Lambda Bedrock 개인정보 추출 실패: {str(e)}")
            raise Exception(f"개인정보 파싱 중 오류가 발생했습니다: {str(e)}")
    
    def test_lambda_connection(self) -> bool:
        """Lambda 함수 연결 테스트"""
        try:
            logger.info(f"🔍 Lambda 함수 연결 테스트 시작: {self.lambda_function_name}")
            
            # 간단한 테스트 페이로드
            test_payload = {
                'extracted_text': '테스트 텍스트입니다.',
                'model_id': self.model_id
            }
            
            response = self.lambda_client.invoke(
                FunctionName=self.lambda_function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(test_payload)
            )
            
            response_payload = json.loads(response['Payload'].read())
            
            if response['StatusCode'] == 200 and response_payload.get('success', False):
                logger.info("✅ Lambda 함수 연결 테스트 성공")
                return True
            else:
                logger.error(f"❌ Lambda 함수 연결 테스트 실패: {response_payload}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Lambda 함수 연결 테스트 오류: {str(e)}")
            return False
