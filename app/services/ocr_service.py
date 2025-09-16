import requests
import base64
import logging
import mimetypes
import os
import time
import json
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class OCRService:
    """Mathpix API를 사용한 OCR 서비스"""
    
    def __init__(self):
        self.app_id = settings.mathpix_app_id
        self.app_key = settings.mathpix_app_key
        
        # API 엔드포인트 정의
        self.api_endpoints = {
            "text": "https://api.mathpix.com/v3/text",      # 이미지/PDF 모두 사용
            "pdf": "https://api.mathpix.com/v3/pdf"         # PDF 전용 (현재 미사용)
        }
        
        # 파일 크기 제한 (bytes)
        self.file_size_limits = {
            "image": 10 * 1024 * 1024,  # 10MB
            "pdf": 20 * 1024 * 1024     # 20MB
        }
        
        logger.info(f" OCR Service 초기화 - App ID: {self.app_id[:10]}..." if self.app_id else "App ID 없음")
        logger.info(f"🔧 OCR Service 초기화 - App Key: {self.app_key[:10]}..." if self.app_key else "App Key 없음")
        logger.info(f"🔧 API 엔드포인트: {self.api_endpoints}")

        if not self.app_id or not self.app_key:
            logger.warning("⚠️ Mathpix API credentials are not set. OCR functionality will be limited or fail.")

    def _get_auth_headers(self) -> dict:
        """인증용 공통 헤더 (Content-Type 미포함)"""
        return {
            "app_id": self.app_id,
            "app_key": self.app_key
        }

    def _get_json_headers(self) -> dict:
        """JSON 요청용 헤더 (인증 + Content-Type)"""
        return {
            **self._get_auth_headers(),
            "Content-type": "application/json"
        }

    def _check_file_size(self, file_path: str, file_type: str) -> bool:
        """파일 크기 제한 확인"""
        try:
            file_size = os.path.getsize(file_path)
            limit = self.file_size_limits.get(file_type, 10 * 1024 * 1024)
            
            logger.info(f" 파일 크기: {file_size} bytes (제한: {limit} bytes)")
            
            if file_size > limit:
                logger.warning(f"⚠️ 파일이 너무 큼: {file_size} bytes > {limit} bytes")
                return False
            return True
        except Exception as e:
            logger.error(f"❌ 파일 크기 확인 실패: {e}")
            return False

    async def extract_text_from_pdf(self, pdf_path: str) -> str:
        """PDF 파일에서 텍스트를 추출합니다 (/v3/pdf 업로드 → md 결과 폴링)."""
        logger.info(f"📄 PDF OCR 시작: {pdf_path}")
        
        if not self.app_id or not self.app_key:
            logger.warning("⚠️ Mathpix API credentials are not configured for PDF extraction.")
            return ""
        
        # 파일 크기 확인
        if not self._check_file_size(pdf_path, "pdf"):
            return ""
        
        try:
            # 1) PDF 업로드 → pdf_id 수신
            headers = self._get_auth_headers()
            logger.info(f"🚀 PDF 업로드 시작: {self.api_endpoints['pdf']}")
            with open(pdf_path, "rb") as f:
                files = {"file": f}
                options = {
                    "conversion_formats": {"md": True},
                    "math_inline_delimiters": ["$", "$"],
                    "math_display_delimiters": ["$$", "$$"]
                }
                data = {"options_json": json.dumps(options)}
                upload_resp = requests.post(
                    self.api_endpoints["pdf"],
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=120
                )
                upload_resp.raise_for_status()
            upload_json = upload_resp.json()
            logger.info(f"✅ PDF 업로드 응답: {list(upload_json.keys())}")
            pdf_id = upload_json.get("pdf_id")
            if not pdf_id:
                logger.error(f"❌ pdf_id 없음: {upload_json}")
                return ""

            # 2) 상태 폴링
            status_url = f"{self.api_endpoints['pdf']}/{pdf_id}"
            logger.info(f"🔄 상태 폴링 시작: {status_url}")
            max_wait_seconds = 300
            interval_seconds = 5
            waited = 0
            status = None
            while waited < max_wait_seconds:
                try:
                    st_resp = requests.get(status_url, headers=self._get_auth_headers(), timeout=60)
                    st_resp.raise_for_status()
                    st_json = st_resp.json()
                    status = st_json.get("status")
                    logger.info(f"   - 현재 상태: {status}")
                    if status == "completed":
                        break
                    if status == "error":
                        logger.error(f"❌ 변환 오류: {st_json}")
                        return ""
                except requests.exceptions.RequestException as e:
                    logger.error(f"❌ 상태 조회 실패: {e}")
                    return ""
                time.sleep(interval_seconds)
                waited += interval_seconds

            if status != "completed":
                logger.error("❌ 시간 초과: 변환이 완료되지 않았습니다")
                return ""

            # 3) 최종 결과(md) 다운로드
            download_url = f"{status_url}.md"
            logger.info(f"📥 결과 다운로드: {download_url}")
            try:
                final_resp = requests.get(download_url, headers=self._get_auth_headers(), timeout=120)
                final_resp.raise_for_status()
                md_text = final_resp.text or ""
                logger.info(f"📝 추출된 텍스트 길이: {len(md_text)} 문자")
                logger.info(f"📝 추출된 텍스트 미리보기 (처음 200자): {md_text[:200]}...")
                return md_text
            except requests.exceptions.RequestException as e:
                logger.error(f"❌ 최종 결과 다운로드 실패: {e}")
                return ""

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ PDF API request failed: {e}")
            return ""
        except Exception as e:
            logger.error(f"❌ Error during PDF OCR text extraction: {e}")
            return ""

    async def extract_text_from_image(self, image_path: str) -> str:
        """이미지 파일에서 텍스트를 추출합니다 (/v3/text 엔드포인트 사용)."""
        logger.info(f"️ 이미지 OCR 시작: {image_path}")
        
        if not self.app_id or not self.app_key:
            logger.warning("⚠️ Mathpix API credentials are not configured for image extraction.")
            return ""
        
        # 파일 크기 확인
        if not self._check_file_size(image_path, "image"):
            return ""
        
        try:
            # 이미지 파일을 base64로 인코딩
            with open(image_path, "rb") as f:
                image_content = f.read()
            
            # 파일 확장자로 MIME 타입 감지
            mime_type, _ = mimetypes.guess_type(image_path)
            if not mime_type or not mime_type.startswith('image/'):
                # 기본값으로 image/jpeg 사용
                mime_type = "image/jpeg"
                logger.warning(f"⚠️ MIME 타입을 감지할 수 없어 기본값 사용: {mime_type}")
            
            base64_image = base64.b64encode(image_content).decode('utf-8')
            logger.info(f"️ 이미지 파일 크기: {len(image_content)} bytes, Base64 길이: {len(base64_image)}")
            logger.info(f"️ 감지된 MIME 타입: {mime_type}")

            # /v3/text 엔드포인트 사용 (JSON)
            payload = {
                "src": f"data:{mime_type};base64,{base64_image}",
                "ocr": ["math", "text"],
                "skip_recrop": True,
                "formats": ["text"]
            }

            logger.info(f"🚀 이미지 API 요청 시작: {self.api_endpoints['text']}")
            response = requests.post(
                self.api_endpoints["text"], 
                headers=self._get_json_headers(), 
                json=payload, 
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"✅ 이미지 API 응답 성공")
            logger.info(f"📊 응답 데이터 키: {list(result.keys())}")
            
            if "text" in result:
                extracted_text = result["text"]
                logger.info(f"📝 추출된 텍스트 길이: {len(extracted_text)} 문자")
                logger.info(f"📝 추출된 텍스트 미리보기 (처음 200자): {extracted_text[:200]}...")
                return extracted_text
            else:
                logger.error(f"❌ 이미지 API did not return 'text' field: {result}")
                return ""
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ 이미지 API request failed: {e}")
            return ""
        except Exception as e:
            logger.error(f"❌ Error during image OCR text extraction: {e}")
            return ""