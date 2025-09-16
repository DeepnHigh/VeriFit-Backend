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
                logger.info(f"📄 문서: {doc.file_name} (타입: {doc.document_type}, MIME: {doc.mime_type}, URL: {doc.file_url})")
            
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
                        logger.info(f"🔍 파일 정보 - 이름: {doc.file_name}, MIME: {doc.mime_type}, 타입: {doc.document_type}")
                        logger.info(f"파일 타입: {type(doc.mime_type)}, {type(doc.document_type)}")
                        logger.info(f"파일 내용: {doc.mime_type}, {doc.document_type}")
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
                            logger.warning(f"⚠️ 지원되지 않는 파일 타입: {doc.mime_type} - 기본적으로 이미지로 처리 시도")
                            # MIME 타입이 명확하지 않은 경우 이미지로 처리 시도
                            extracted_text = await self.ocr_service.extract_text_from_image(file_path)
                        
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
            
            # 4-1. 결합된 전체 텍스트를 DB(job_seekers.full_text)에 저장
            try:
                job_seeker.full_text = combined_text
                self.db.add(job_seeker)
                self.db.commit()
                logger.info("💾 job_seekers.full_text 저장 완료")
            except Exception as e:
                logger.error(f"❌ full_text 저장 실패: {e}")
                self.db.rollback()
            
            # 5. AWS Lambda(Bedrock)으로 개인정보 추출
            logger.info(f"🤖 LLM 개인정보 추출 시작...")
            personal_info = await self.bedrock_service.extract_personal_info(combined_text)
            logger.info(f"🎉 LLM 개인정보 추출 완료!")
            logger.info(f"📊 최종 추출 결과: {personal_info}")

            # 5-1. LLM 결과를 job_seekers 테이블에 반영
            try:
                # personal_info는 Pydantic 모델 또는 dict 호환
                pi = personal_info if isinstance(personal_info, dict) else personal_info.model_dump()
                # None이 아닌 값만 업데이트
                if pi.get('full_name') is not None:
                    job_seeker.full_name = pi['full_name']
                if pi.get('phone') is not None:
                    job_seeker.phone = pi['phone']
                if pi.get('email') is not None:
                    job_seeker.email = pi['email']
                if pi.get('education_level') is not None:
                    # 한글 학력명을 내부 enum 값으로 매핑
                    edu_raw = (pi['education_level'] or '').strip().lower()
                    edu_map = {
                        '고졸': 'high_school',
                        '고등학교': 'high_school',
                        '전문학사': 'associate',
                        '학사': 'bachelor',
                        '석사': 'master',
                        '박사': 'phd'
                    }
                    # 이미 영문 enum 값이 들어오는 경우도 허용
                    normalized = edu_map.get(edu_raw, edu_raw)
                    job_seeker.education_level = normalized if normalized in (
                        'high_school','associate','bachelor','master','phd'
                    ) else None
                if pi.get('university') is not None:
                    job_seeker.university = pi['university']
                if pi.get('major') is not None:
                    job_seeker.major = pi['major']
                if pi.get('graduation_year') is not None:
                    # 숫자 변환 시도
                    try:
                        job_seeker.graduation_year = int(pi['graduation_year']) if pi['graduation_year'] is not None else None
                    except Exception:
                        pass
                if pi.get('total_experience_years') is not None:
                    try:
                        job_seeker.total_experience_years = int(pi['total_experience_years'])
                    except Exception:
                        pass
                if pi.get('company_name') is not None:
                    job_seeker.company_name = pi['company_name']

                self.db.add(job_seeker)
                self.db.commit()
                logger.info("💾 job_seekers 프로필 필드 업데이트 완료")
            except Exception as e:
                logger.error(f"❌ job_seekers 업데이트 실패: {e}")
                self.db.rollback()
            
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
