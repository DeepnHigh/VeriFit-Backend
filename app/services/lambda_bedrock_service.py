import boto3
import json
import logging
from typing import Dict, Any, Optional
from app.core.config import settings
from app.schemas.personal_info import PersonalInfo

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
        
        # Lambda 클라이언트 초기화
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
            
            logger.info(f"🚀 Lambda 함수 호출 시작...")
            logger.info(f"🔧 Lambda 함수: {self.lambda_function_name}")
            
            # Lambda 함수 호출
            response = self.lambda_client.invoke(
                FunctionName=self.lambda_function_name,
                InvocationType='RequestResponse',  # 동기 호출
                Payload=json.dumps(payload)
            )
            
            logger.info(f"✅ Lambda 함수 응답 수신")
            
            # 응답 파싱
            response_payload = json.loads(response['Payload'].read())
            
            if response['StatusCode'] != 200:
                logger.error(f"❌ Lambda 함수 오류: {response_payload}")
                raise Exception(f"Lambda 함수 실행 실패: {response_payload.get('error', 'Unknown error')}")
            
            if not response_payload.get('success', False):
                logger.error(f"❌ Lambda 함수 처리 실패: {response_payload}")
                raise Exception(f"Lambda 함수 처리 실패: {response_payload.get('error', 'Unknown error')}")
            
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
