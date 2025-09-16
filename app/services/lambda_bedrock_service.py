import httpx  # urllib 대신 httpx 사용
import aioboto3 # boto3 대신 aioboto3 사용
import json
import logging
from typing import Dict, Any, Optional
from app.core.config import settings
from app.schemas.personal_info import PersonalInfo
from botocore.session import get_session
from botocore.auth import SigV4Auth
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class LambdaBedrockService:
    """AWS Lambda를 통한 Bedrock LLM 서비스 (비동기 최적화)"""

    def __init__(self):
        self.region = settings.aws_region
        self.model_id = settings.bedrock_model_id
        self.lambda_function_name = getattr(settings, 'lambda_function_name', 'verifit-bedrock-extractor')
        self.lambda_function_url: Optional[str] = getattr(settings, 'lambda_function_url', None)
        self.lambda_function_url_auth: Optional[str] = getattr(settings, 'lambda_function_url_auth', 'NONE')
        
        logger.info(f"🔧 Lambda Bedrock Service 초기화 - Region: {self.region}")
        if self.lambda_function_url:
            logger.info(f"🌐 Lambda Function URL 사용: {self.lambda_function_url}")
        else:
            logger.info(f"🔧 Lambda SDK Invoke 사용: {self.lambda_function_name}")

    def _get_sigv4_headers(self, url: str, body: bytes) -> Dict[str, str]:
        """SigV4 서명 헤더를 생성하는 헬퍼 함수"""
        parsed_url = urlparse(url)
        host = parsed_url.hostname
        # URL에서 리전 정보를 더 안정적으로 추출
        region = host.split('.')[2] if len(host.split('.')) > 3 else self.region

        session = get_session()
        credentials = session.get_credentials()
        
        # botocore.awsrequest.AWSRequest 대신 httpx.Request 사용 준비
        request = httpx.Request('POST', url, content=body, headers={'Content-Type': 'application/json', 'host': host})
        
        # botocore의 서명 로직을 사용
        signer = SigV4Auth(credentials, 'lambda', region)
        # request 객체를 직접 수정하는 대신, 서명된 헤더를 반환받아 사용
        # 이를 위해선 botocore.awsrequest.AWSRequest 객체를 생성해야 함
        from botocore.awsrequest import AWSRequest
        aws_request = AWSRequest(method=request.method, url=url, data=request.content, headers=request.headers)
        signer.add_auth(aws_request)
        
        return dict(aws_request.headers.items())


    async def _invoke_via_url_async(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """(비동기) Function URL을 통해 Lambda 함수를 호출합니다."""
        logger.info("🚀 Function URL(async)로 호출 시작...")
        headers = {'Content-Type': 'application/json'}
        data_bytes = json.dumps(payload).encode('utf-8')

        if (self.lambda_function_url_auth or '').upper() == 'AWS_IAM':
            logger.info("🔑 SigV4 서명 추가 중...")
            headers = self._get_sigv4_headers(self.lambda_function_url, data_bytes)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.lambda_function_url,
                content=data_bytes,
                headers=headers,
                timeout=60.0
            )
            response.raise_for_status() # HTTP 4xx/5xx 에러 시 예외 발생
            return response.json()

    async def _invoke_via_sdk_async(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """(비동기) AWS SDK (aioboto3)를 통해 Lambda 함수를 호출합니다."""
        logger.info(f"🚀 Lambda SDK(async)로 '{self.lambda_function_name}' 호출 시작...")
        session = aioboto3.Session()
        async with session.client("lambda", region_name=self.region) as lambda_client:
            response = await lambda_client.invoke(
                FunctionName=self.lambda_function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            payload_bytes = await response['Payload'].read()
            return json.loads(payload_bytes)

    async def extract_personal_info(self, extracted_text: str) -> PersonalInfo:
        """Lambda를 통해 개인정보 추출 (로직 단순화 및 비동기 최적화)"""
        logger.info(f"🤖 Lambda Bedrock 개인정보 추출 시작 (async)")
        
        # 페이로드 크기 제한
        MAX_PAYLOAD_CHARS = 10000
        if len(extracted_text) > MAX_PAYLOAD_CHARS:
            extracted_text = extracted_text[:MAX_PAYLOAD_CHARS]
            logger.warning(f"⚠️ 텍스트가 너무 길어 {MAX_PAYLOAD_CHARS}자로 축소됨")

        payload = {'extracted_text': extracted_text, 'model_id': self.model_id}
        
        try:
            # 설정에 따라 URL 방식 또는 SDK 방식을 선택 (복잡한 fallback 제거)
            if self.lambda_function_url:
                response_payload = await self._invoke_via_url_async(payload)
            else:
                response_payload = await self._invoke_via_sdk_async(payload)
            
            logger.info("✅ Lambda 함수 응답 수신 성공")

            # 응답 성공 여부 확인
            if not response_payload.get('success', False):
                error_msg = response_payload.get('error', 'Unknown error from Lambda')
                logger.error(f"❌ Lambda 처리 실패: {error_msg}")
                raise Exception(f"Lambda 처리 실패: {error_msg}")
            
            # 결과 파싱
            personal_info_data = response_payload.get('personal_info', {})
            logger.info(f"📝 LLM 원본 응답: {response_payload.get('raw_response', '')}")

            personal_info = PersonalInfo(**personal_info_data) # pydantic 모델 직접 생성
            
            logger.info(f"✅ Lambda Bedrock 개인정보 추출 완료: {personal_info}")
            return personal_info

        except httpx.HTTPStatusError as e:
            # httpx 에러 처리
            error_body = e.response.text
            logger.error(f"❌ Function URL 호출 실패: {e.response.status_code} - {error_body}")
            raise Exception(f"Lambda 함수 호출에 실패했습니다: {error_body}")
        except Exception as e:
            # 기타 모든 에러
            logger.error(f"❌ Lambda Bedrock 개인정보 추출 중 심각한 오류: {str(e)}")
            raise Exception(f"개인정보 파싱 중 오류가 발생했습니다: {str(e)}")