import os
import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.job_seeker import JobSeeker
from app.models.job_seeker_document import JobSeekerDocument
from app.services.ocr_service import OCRService
from app.services.lambda_bedrock_service import LambdaBedrockService
from app.schemas.personal_info import PersonalInfo, PersonalInfoResponse
import uuid

logger = logging.getLogger(__name__)

class PersonalInfoService:
    """개인정보 파싱 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ocr_service = OCRService()
        self.bedrock_service = LambdaBedrockService()
    
    async def parse_personal_info(self, user_id: str) -> PersonalInfoResponse:
        """사용자의 모든 문서에서 개인정보 추출"""
        logger.info(f"🔍 개인정보 파싱 시작 - User ID: {user_id}")
        
        try:
            # 1. 사용자 확인
            uid = self._to_uuid(user_id)
            job_seeker = self.db.query(JobSeeker).filter(JobSeeker.user_id == uid).first()
            
            if not job_seeker:
                logger.warning(f"❌ 구직자 정보를 찾을 수 없습니다 - User ID: {user_id}")
                return PersonalInfoResponse(
                    success=False,
                    personal_info=PersonalInfo(),
                    extracted_text_length=0,
                    processed_files=[],
                    message="구직자 정보를 찾을 수 없습니다"
                )
            
            logger.info(f"✅ 구직자 정보 확인 완료 - Job Seeker ID: {job_seeker.id}")
            
            # 2. 사용자의 모든 문서 조회
            documents = self.db.query(JobSeekerDocument).filter(
                JobSeekerDocument.job_seeker_id == job_seeker.id
            ).all()
            
            logger.info(f"📁 발견된 문서 수: {len(documents)}")
            for doc in documents:
                logger.info(f"📄 문서: {doc.file_name} (타입: {doc.document_type}, MIME: {doc.mime_type})")
            
            if not documents:
                return PersonalInfoResponse(
                    success=False,
                    personal_info=PersonalInfo(),
                    extracted_text_length=0,
                    processed_files=[],
                    message="업로드된 문서가 없습니다"
                )
            
            # 3. 각 문서에서 텍스트 추출
            logger.info(f"📝 텍스트 추출 시작 - {len(documents)}개 문서 처리")
            all_text = []
            processed_files = []
            
            for doc in documents:
                try:
                    logger.info(f"🔄 문서 처리 중: {doc.file_name}")
                    # 파일 경로 생성 (로컬 파일 시스템 기준)
                    file_path = self._get_local_file_path(doc.file_url)
                    logger.info(f"📁 파일 경로: {file_path}")
                    
                    if os.path.exists(file_path):
                        logger.info(f"✅ 파일 존재 확인 - {doc.file_name}")
                        
                        # 파일 타입에 따라 적절한 OCR 메서드 호출
                        extracted_text = None
                        if doc.mime_type == "application/pdf":
                            logger.info(f"📄 PDF 파일 처리: {doc.file_name}")
                            extracted_text = await self.ocr_service.extract_text_from_pdf(file_path)
                        elif doc.mime_type.startswith("image/"):
                            logger.info(f"🖼️ 이미지 파일 처리: {doc.file_name}")
                            extracted_text = await self.ocr_service.extract_text_from_image(file_path)
                        elif doc.mime_type == "text/plain" or doc.document_type == "github":
                            logger.info(f"📝 텍스트 파일 처리: {doc.file_name}")
                            # 텍스트 파일은 직접 읽기
                            with open(file_path, "r", encoding="utf-8") as f:
                                extracted_text = f.read()
                        else:
                            logger.warning(f"⚠️ 지원되지 않는 파일 타입: {doc.mime_type}")
                        
                        if extracted_text:
                            all_text.append(extracted_text)
                            processed_files.append(doc.file_name)
                            logger.info(f"✅ 텍스트 추출 성공 - {doc.file_name} (길이: {len(extracted_text)} 문자)")
                            logger.info(f"📝 추출된 텍스트 미리보기: {extracted_text[:100]}...")
                        else:
                            logger.warning(f"⚠️ 텍스트 추출 실패 - {doc.file_name}")
                    else:
                        logger.warning(f"❌ 파일을 찾을 수 없음: {file_path}")
                        
                except Exception as e:
                    logger.error(f"❌ 문서 처리 중 오류 - {doc.file_name}: {str(e)}")
                    continue
            
            if not all_text:
                return PersonalInfoResponse(
                    success=False,
                    personal_info=PersonalInfo(),
                    extracted_text_length=0,
                    processed_files=processed_files,
                    message="텍스트 추출에 실패했습니다"
                )
            
            # 4. 모든 텍스트를 하나로 합치기
            combined_text = "\n\n".join(all_text)
            logger.info(f"📝 전체 텍스트 결합 완료 - 총 길이: {len(combined_text)} 문자")
            logger.info(f"📝 결합된 텍스트 미리보기 (처음 200자): {combined_text[:200]}...")
            
            # 5. AWS Bedrock으로 개인정보 추출
            logger.info(f"🤖 LLM 개인정보 추출 시작...")
            personal_info = await self.bedrock_service.extract_personal_info(combined_text)
            logger.info(f"🎉 LLM 개인정보 추출 완료!")
            logger.info(f"📊 최종 추출 결과: {personal_info}")
            
            return PersonalInfoResponse(
                success=True,
                personal_info=personal_info,
                extracted_text_length=len(combined_text),
                processed_files=processed_files,
                message=f"{len(processed_files)}개 파일에서 개인정보를 성공적으로 추출했습니다"
            )
            
        except Exception as e:
            logger.error(f"Personal info parsing failed: {str(e)}")
            return PersonalInfoResponse(
                success=False,
                personal_info=PersonalInfo(),
                extracted_text_length=0,
                processed_files=[],
                message=f"개인정보 파싱 중 오류가 발생했습니다: {str(e)}"
            )
    
    def _to_uuid(self, user_id: str | uuid.UUID) -> uuid.UUID:
        """문자열을 UUID로 변환"""
        if isinstance(user_id, str):
            return uuid.UUID(user_id)
        return user_id
    
    def _get_local_file_path(self, file_url: str) -> str:
        """파일 URL에서 로컬 파일 경로 생성"""
        from app.core.config import settings
        
        # URL에서 파일 경로 추출
        # 예: {api_base_url}/files/user_id/document_type/filename
        # -> uploads/user_id/document_type/filename
        
        files_path = f"{settings.api_base_url}/files/"
        if files_path in file_url:
            relative_path = file_url.split(files_path)[1]
            return os.path.join("uploads", relative_path)
        else:
            # 다른 URL 형식 처리
            return file_url
