import requests
import base64
import logging
from typing import Optional
from app.core.config import settings
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

class OCRService:
    """Mathpix API를 사용한 OCR 서비스"""
    
    def __init__(self):
        self.app_id = settings.mathpix_app_id
        self.app_key = settings.mathpix_app_key
        self.api_url = "https://api.mathpix.com/v3/text"
        
        logger.info(f"🔧 OCR Service 초기화 - App ID: {self.app_id[:10]}..." if self.app_id else "App ID 없음")
        logger.info(f"🔧 OCR Service 초기화 - App Key: {self.app_key[:10]}..." if self.app_key else "App Key 없음")

        if not self.app_id or not self.app_key:
            logger.warning("⚠️ Mathpix API credentials are not set. OCR functionality will be limited or fail.")

    async def extract_text_from_pdf(self, pdf_path: str) -> str:
        """PDF 파일에서 텍스트를 추출합니다."""
        logger.info(f"📄 PDF OCR 시작: {pdf_path}")
        
        if not self.app_id or not self.app_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Mathpix API credentials are not configured."
            )
        
        try:
            with open(pdf_path, "rb") as f:
                pdf_content = f.read()
            
            base64_pdf = base64.b64encode(pdf_content).decode('utf-8')
            logger.info(f"📄 PDF 파일 크기: {len(pdf_content)} bytes, Base64 길이: {len(base64_pdf)}")

            headers = {
                "app_id": self.app_id,
                "app_key": self.app_key,
                "Content-type": "application/json"
            }
            payload = {
                "src": f"data:application/pdf;base64,{base64_pdf}",
                "ocr": ["math", "text"],
                "skip_recrop": True,
                "formats": ["text"]
            }

            logger.info(f"🚀 Mathpix API 요청 시작...")
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"✅ Mathpix API 응답 성공")
            logger.info(f"📊 응답 데이터 키: {list(result.keys())}")
            
            if "text" in result:
                extracted_text = result["text"]
                logger.info(f"📝 추출된 텍스트 길이: {len(extracted_text)} 문자")
                logger.info(f"📝 추출된 텍스트 미리보기 (처음 200자): {extracted_text[:200]}...")
                return extracted_text
            else:
                logger.error(f"❌ Mathpix API did not return 'text' field: {result}")
                # 오류가 있어도 빈 문자열 반환하여 다른 파일 처리를 계속할 수 있도록 함
                return ""
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Mathpix API request failed: {e}")
            return ""
        except Exception as e:
            logger.error(f"❌ Error during OCR text extraction: {e}")
            return ""

    async def extract_text_from_image(self, image_path: str) -> str:
        """이미지 파일에서 텍스트를 추출합니다."""
        logger.info(f"🖼️ 이미지 OCR 시작: {image_path}")
        
        if not self.app_id or not self.app_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Mathpix API credentials are not configured."
            )
        
        try:
            with open(image_path, "rb") as f:
                image_content = f.read()
            
            base64_image = base64.b64encode(image_content).decode('utf-8')
            mime_type = "image/jpeg"  # 또는 image/png 등 실제 이미지 타입에 맞게 조정 필요
            logger.info(f"🖼️ 이미지 파일 크기: {len(image_content)} bytes, Base64 길이: {len(base64_image)}")

            headers = {
                "app_id": self.app_id,
                "app_key": self.app_key,
                "Content-type": "application/json"
            }
            payload = {
                "src": f"data:{mime_type};base64,{base64_image}",
                "ocr": ["math", "text"],
                "skip_recrop": True,
                "formats": ["text"]
            }

            logger.info(f"🚀 Mathpix API 요청 시작...")
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"✅ Mathpix API 응답 성공")
            logger.info(f"📊 응답 데이터 키: {list(result.keys())}")
            
            if "text" in result:
                extracted_text = result["text"]
                logger.info(f"📝 추출된 텍스트 길이: {len(extracted_text)} 문자")
                logger.info(f"📝 추출된 텍스트 미리보기 (처음 200자): {extracted_text[:200]}...")
                return extracted_text
            else:
                logger.error(f"❌ Mathpix API did not return 'text' field for image: {result}")
                return ""
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Mathpix API image request failed: {e}")
            return ""
        except Exception as e:
            logger.error(f"❌ Error during OCR image text extraction: {e}")
            return ""