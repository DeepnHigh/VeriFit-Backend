import httpx  # urllib 대신 httpx 사용
import boto3
from starlette.concurrency import run_in_threadpool
import json
import logging
from typing import Dict, Any, Optional, List
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
        # KB ingest 전용
        self.lambda_kb_ingest_function_name: Optional[str] = getattr(settings, 'lambda_kb_ingest_function_name', 'verifit-kb-ingest')
        self.lambda_kb_ingest_function_url: Optional[str] = getattr(settings, 'lambda_kb_ingest_function_url', None)
        # Evaluation 전용
        self.lambda_evaluation_function_name: Optional[str] = getattr(settings, 'lambda_evaluation_function_name', 'verifit-evaluate-candidate')
        self.lambda_evaluation_function_url: Optional[str] = getattr(settings, 'lambda_evaluation_function_url', None)
        
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


    async def _invoke_via_url_async(self, payload: Dict[str, Any], override_url: Optional[str] = None) -> Dict[str, Any]:
        """(비동기) Function URL을 통해 Lambda 함수를 호출합니다."""
        logger.info("🚀 Function URL(async)로 호출 시작...")
        headers = {'Content-Type': 'application/json'}
        data_bytes = json.dumps(payload).encode('utf-8')

        target_url = override_url or self.lambda_function_url
        print(f"[DEBUG] Function URL 호출 - Target URL: {target_url}")
        print(f"[DEBUG] Override URL: {override_url}")
        print(f"[DEBUG] Default URL: {self.lambda_function_url}")
        
        if not target_url:
            raise ValueError("Function URL이 구성되지 않았습니다.")

        if (self.lambda_function_url_auth or '').upper() == 'AWS_IAM':
            logger.info("🔑 SigV4 서명 추가 중...")
            headers = self._get_sigv4_headers(target_url, data_bytes)

        print(f"[DEBUG] HTTP 요청 시작 - URL: {target_url}")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                target_url,
                content=data_bytes,
                headers=headers,
                timeout=300.0
            )
            print(f"[DEBUG] HTTP 응답 - Status: {response.status_code}")
            print(f"[DEBUG] HTTP 응답 - Body: {response.text}")
            response.raise_for_status() # HTTP 4xx/5xx 에러 시 예외 발생
            return response.json()

    async def _invoke_via_sdk_async(self, payload: Dict[str, Any], function_name: str = None) -> Dict[str, Any]:
        """(비동기) AWS SDK (aioboto3)를 통해 Lambda 함수를 호출합니다."""
        target_function = function_name or self.lambda_function_name
        logger.info(f"🚀 Lambda SDK 호출(start sync boto3 in threadpool)로 '{target_function}' 호출 시작...")

        def invoke_sync():
            # boto3 client는 동기이므로 threadpool에서 실행
            client = boto3.client('lambda', region_name=self.region)
            response = client.invoke(
                FunctionName=target_function,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload).encode('utf-8')
            )
            # response['Payload']는 botocore.response.StreamingBody
            payload_bytes = response['Payload'].read()
            try:
                return json.loads(payload_bytes)
            except Exception:
                # payload가 이미 dict인 경우도 있어서 안전하게 처리
                return payload_bytes

        return await run_in_threadpool(invoke_sync)

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
    
    async def generate_interview_questions(self, job_posting_data: Dict[str, Any]) -> Dict[str, Any]:
        """Lambda를 통해 면접 질문 생성"""
        logger.info(f"🤖 Lambda Bedrock 면접 질문 생성 시작")
        
        payload = {
            'job_posting_data': job_posting_data
        }
        
        try:
            # 질문 생성 전용 Lambda 함수 호출
            questions_function_name = getattr(settings, 'lambda_questions_function_name', 'verifit-generate-questions')
            
            # 설정에 따라 URL 방식 또는 SDK 방식을 선택 (질문 전용 URL 우선)
            questions_function_url = getattr(settings, 'lambda_questions_function_url', None)
            if questions_function_url:
                response_payload = await self._invoke_via_url_async(payload, questions_function_url)
            elif self.lambda_function_url:
                response_payload = await self._invoke_via_url_async(payload)
            else:
                response_payload = await self._invoke_via_sdk_async(payload, questions_function_name)
            
            logger.info("✅ Lambda 함수 응답 수신 성공")

            # 응답 성공 여부 확인
            if not response_payload.get('success', False):
                error_msg = response_payload.get('error', 'Unknown error from Lambda')
                logger.error(f"❌ Lambda 처리 실패: {error_msg}")
                raise Exception(f"Lambda 처리 실패: {error_msg}")
            
            # 결과 파싱
            questions_data = response_payload.get('questions', [])
            logger.info(f"📝 생성된 질문 수: {len(questions_data) if isinstance(questions_data, list) else 'Unknown'}")

            return {
                'success': True,
                'questions': questions_data,
                'raw_response': response_payload.get('raw_response', '')
            }

        except httpx.HTTPStatusError as e:
            # httpx 에러 처리
            error_body = e.response.text
            logger.error(f"❌ Function URL 호출 실패: {e.response.status_code} - {error_body}")
            raise Exception(f"Lambda 함수 호출에 실패했습니다: {error_body}")
        except Exception as e:
            # 기타 모든 에러
            logger.error(f"❌ Lambda Bedrock 면접 질문 생성 중 심각한 오류: {str(e)}")
            raise Exception(f"면접 질문 생성 중 오류가 발생했습니다: {str(e)}")
    
    async def generate_interview_answer(self, prompt: str) -> Dict[str, Any]:
        """Lambda를 통해 면접 답변 생성"""
        logger.info(f"🤖 Lambda Bedrock 면접 답변 생성 시작")
        
        # 페이로드 크기 제한
        MAX_PAYLOAD_CHARS = 10000
        if len(prompt) > MAX_PAYLOAD_CHARS:
            prompt = prompt[:MAX_PAYLOAD_CHARS]
            logger.warning(f"⚠️ 프롬프트가 너무 길어 {MAX_PAYLOAD_CHARS}자로 축소됨")

        payload = {
            'prompt': prompt, 
            'model_id': self.model_id,
            'task_type': 'generate_interview_answer'
        }
        
        try:
            # 설정에 따라 URL 방식 또는 SDK 방식을 선택
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
            answer = response_payload.get('answer', '')
            logger.info(f"📝 생성된 답변 길이: {len(answer)}")

            return {
                'success': True,
                'answer': answer,
                'raw_response': response_payload.get('raw_response', '')
            }

        except httpx.HTTPStatusError as e:
            # httpx 에러 처리
            error_body = e.response.text
            logger.error(f"❌ Function URL 호출 실패: {e.response.status_code} - {error_body}")
            raise Exception(f"Lambda 함수 호출에 실패했습니다: {error_body}")
        except Exception as e:
            # 기타 모든 에러
            logger.error(f"❌ Lambda Bedrock 면접 답변 생성 중 심각한 오류: {str(e)}")
            raise Exception(f"면접 답변 생성 중 오류가 발생했습니다: {str(e)}")
    
    async def generate_evaluation(self, prompt: str) -> Dict[str, Any]:
        """Lambda를 통해 최종 평가 생성"""
        logger.info(f"🤖 Lambda Bedrock 최종 평가 생성 시작")
        
        # 페이로드 크기 제한
        MAX_PAYLOAD_CHARS = 15000
        if len(prompt) > MAX_PAYLOAD_CHARS:
            prompt = prompt[:MAX_PAYLOAD_CHARS]
            logger.warning(f"⚠️ 프롬프트가 너무 길어 {MAX_PAYLOAD_CHARS}자로 축소됨")

        payload = {
            'prompt': prompt, 
            'model_id': self.model_id,
            'task_type': 'generate_evaluation'
        }
        
        try:
            # 설정에 따라 URL 방식 또는 SDK 방식을 선택
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
            evaluation_data = response_payload.get('evaluation', {})
            logger.info(f"📝 생성된 평가 결과: {list(evaluation_data.keys()) if isinstance(evaluation_data, dict) else 'Unknown'}")

            return {
                'success': True,
                'evaluation': evaluation_data,
                'raw_response': response_payload.get('raw_response', '')
            }

        except httpx.HTTPStatusError as e:
            # httpx 에러 처리
            error_body = e.response.text
            logger.error(f"❌ Function URL 호출 실패: {e.response.status_code} - {error_body}")
            raise Exception(f"Lambda 함수 호출에 실패했습니다: {error_body}")
        except Exception as e:
            # 기타 모든 에러
            logger.error(f"❌ Lambda Bedrock 최종 평가 생성 중 심각한 오류: {str(e)}")
            raise Exception(f"최종 평가 생성 중 오류가 발생했습니다: {str(e)}")
    
    async def evaluate_candidate(self, questions: List[str], job_seeker_data: Dict[str, Any], job_posting_skills: Dict[str, Any], applicant_id: str = None, job_posting_id: str = None) -> Dict[str, Any]:
        """Lambda를 통해 지원자 평가"""
        logger.info(f"🤖 Lambda Bedrock 지원자 평가 시작")
        
        payload = {
            'questions': questions,
            'job_seeker_data': job_seeker_data,
            'job_posting_skills': job_posting_skills
        }
        
        # KB 참조를 위한 파라미터 추가
        if applicant_id:
            payload['applicant_id'] = applicant_id
        if job_posting_id:
            payload['job_posting_id'] = job_posting_id
        
        try:
            # 지원자 평가 전용 Lambda 함수 호출
            # 설정에 따라 URL 방식 또는 SDK 방식을 선택 (평가용 전용 설정 우선)
            evaluation_function_name = self.lambda_evaluation_function_name
            evaluation_function_url = self.lambda_evaluation_function_url

            if evaluation_function_url:
                response_payload = await self._invoke_via_url_async(payload, override_url=evaluation_function_url)
            else:
                response_payload = await self._invoke_via_sdk_async(payload, evaluation_function_name)
            
            # Function URL 방식은 {statusCode, body} 형태일 수 있으므로 처리
            if isinstance(response_payload, dict) and 'statusCode' in response_payload and 'body' in response_payload:
                try:
                    parsed_body = json.loads(response_payload['body']) if isinstance(response_payload['body'], str) else response_payload['body']
                except Exception:
                    parsed_body = {"success": False, "error": "invalid_body"}
                response_payload = parsed_body

            logger.info("✅ Lambda 함수 응답 수신 성공")

            # 응답 성공 여부 확인
            if not response_payload.get('success', False):
                error_msg = response_payload.get('error', 'Unknown error from Lambda')
                logger.error(f"❌ Lambda 처리 실패: {error_msg}")
                raise Exception(f"Lambda 처리 실패: {error_msg}")
            
            # 결과 파싱
            evaluation_data = response_payload.get('evaluation', {})
            conversations = response_payload.get('conversations', [])
            logger.info(f"📝 생성된 평가 결과: {list(evaluation_data.keys()) if isinstance(evaluation_data, dict) else 'Unknown'}")

            return {
                'success': True,
                'evaluation': evaluation_data,
                'conversations': conversations,
                'raw_response': response_payload.get('raw_response', '')
            }

        except httpx.HTTPStatusError as e:
            # httpx 에러 처리
            error_body = e.response.text
            logger.error(f"❌ Function URL 호출 실패: {e.response.status_code} - {error_body}")
            raise Exception(f"Lambda 함수 호출에 실패했습니다: {error_body}")
        except Exception as e:
            # 기타 모든 에러
            logger.error(f"❌ Lambda Bedrock 지원자 평가 중 심각한 오류: {str(e)}")
            raise Exception(f"지원자 평가 중 오류가 발생했습니다: {str(e)}")

    async def ingest_applicant_kb(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """지원자 KB 인덱싱 Lambda 호출 (full_text/behavior_text/big5_text 업로드+인덱싱)"""
        try:
            print(f"[DEBUG] KB 업로드 시작 - URL: {self.lambda_kb_ingest_function_url}")
            print(f"[DEBUG] KB 업로드 Payload: {payload}")
            
            # URL 우선, 없으면 함수명으로 호출
            if self.lambda_kb_ingest_function_url:
                print(f"[DEBUG] Function URL 방식으로 호출")
                resp = await self._invoke_via_url_async(payload, override_url=self.lambda_kb_ingest_function_url)
            else:
                print(f"[DEBUG] SDK 방식으로 호출 - 함수명: {self.lambda_kb_ingest_function_name}")
                resp = await self._invoke_via_sdk_async(payload, self.lambda_kb_ingest_function_name)
            
            print(f"[DEBUG] KB 업로드 원본 응답: {resp}")
            if not isinstance(resp, dict):
                return {"success": False, "error": "invalid_response"}
            # Function URL 방식은 {statusCode, body} 형태일 수 있음
            if 'statusCode' in resp and 'body' in resp:
                try:
                    body = json.loads(resp['body']) if isinstance(resp['body'], str) else resp['body']
                except Exception:
                    body = {"success": False, "error": "invalid_body"}
                return body
            return resp
        except Exception as e:
            return {"success": False, "error": str(e)}