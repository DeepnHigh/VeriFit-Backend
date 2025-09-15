from sqlalchemy.orm import Session, joinedload
from fastapi import UploadFile, HTTPException, status
from app.models.job_seeker import JobSeeker
from app.models.big5_test_result import Big5TestResult
from app.models.ai_learning_answer import AILearningAnswer
from app.models.ai_learning_question import AILearningQuestion
from app.models.job_seeker_document import JobSeekerDocument
from app.services.s3_service import S3Service
import uuid
import logging

logger = logging.getLogger(__name__)

class JobSeekerService:
    def __init__(self, db: Session):
        self.db = db
        self.s3_service = S3Service()
    
    def _to_uuid(self, user_id: str | uuid.UUID) -> uuid.UUID:
        if isinstance(user_id, uuid.UUID):
            return user_id
        return uuid.UUID(str(user_id))

    def _get_by_user_id(self, user_id: str | uuid.UUID) -> JobSeeker | None:
        uid = self._to_uuid(user_id)
        return self.db.query(JobSeeker).filter(JobSeeker.user_id == uid).first()

    def get_applicant_profile(self, user_id: str | uuid.UUID) -> JobSeeker | None:
        """지원자 마이페이지 정보 조회: JobSeeker ORM 객체 반환"""
        return self._get_by_user_id(user_id)
    
    def create_bio(self, user_id: str | uuid.UUID, bio: str) -> JobSeeker:
        """지원자 짧은소개 등록"""
        applicant = self._get_by_user_id(user_id)
        if not applicant:
            applicant = JobSeeker(user_id=self._to_uuid(user_id), bio=bio)
            self.db.add(applicant)
        else:
            applicant.bio = bio
        
        self.db.commit()
        self.db.refresh(applicant)
        return applicant
    
    def update_bio(self, user_id: str | uuid.UUID, bio: str) -> JobSeeker:
        """지원자 짧은소개 수정"""
        return self.create_bio(user_id, bio)
    
    def create_applicant_info(self, user_id: str | uuid.UUID, info_data: dict) -> JobSeeker:
        """지원자 기본정보 등록"""
        applicant = self._get_by_user_id(user_id)
        if not applicant:
            applicant = JobSeeker(user_id=self._to_uuid(user_id), **info_data)
            self.db.add(applicant)
        else:
            for key, value in info_data.items():
                setattr(applicant, key, value)
        
        self.db.commit()
        self.db.refresh(applicant)
        return applicant
    
    def update_applicant_info(self, user_id: str | uuid.UUID, info_data: dict) -> JobSeeker:
        """지원자 기본정보 수정"""
        return self.create_applicant_info(user_id, info_data)
    
    def get_mypage_data(self, user_id: str | uuid.UUID) -> dict:
        """마이페이지용 종합 데이터 조회"""
        uid = self._to_uuid(user_id)
        
        # 1. JobSeeker 기본 정보 조회
        job_seeker = self.db.query(JobSeeker).filter(JobSeeker.user_id == uid).first()
        
        if not job_seeker:
            return None
        
        # 2. Big5 성격검사 결과 조회
        big5_results = self.db.query(Big5TestResult).filter(
            Big5TestResult.job_seeker_id == job_seeker.id
        ).all()
        
        # 3. AI 학습 응답 조회 (질문 정보 포함)
        ai_learning_answers = self.db.query(AILearningAnswer).options(
            joinedload(AILearningAnswer.question)
        ).filter(
            AILearningAnswer.job_seeker_id == job_seeker.id
        ).all()
        
        # 4. 문서 조회
        documents = self.db.query(JobSeekerDocument).filter(
            JobSeekerDocument.job_seeker_id == job_seeker.id
        ).all()
        
        # 결과를 딕셔너리로 구성
        return {
            'job_seeker': job_seeker,
            'big5_test_results': big5_results,
            'ai_learning_answers': ai_learning_answers,
            'documents': documents
        }
    
    async def upload_file(self, user_id: str | uuid.UUID, document_type: str, file: UploadFile) -> dict:
        """S3 파일 업로드 및 DB 저장"""
        try:
            # 1. JobSeeker 존재 확인
            uid = self._to_uuid(user_id)
            job_seeker = self.db.query(JobSeeker).filter(JobSeeker.user_id == uid).first()
            
            if not job_seeker:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="구직자 정보를 찾을 수 없습니다"
                )
            
            # 2. S3에 파일 업로드
            upload_result = await self.s3_service.upload_file(
                file=file,
                user_id=str(user_id),
                document_type=document_type
            )
            
            if not upload_result["success"]:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=upload_result["error"]
                )
            
            # 3. 데이터베이스에 문서 정보 저장
            document = JobSeekerDocument(
                job_seeker_id=job_seeker.id,
                document_type=document_type,
                file_name=upload_result["original_filename"],
                file_url=upload_result["file_url"],
                file_size=upload_result["file_size"],
                mime_type=upload_result["content_type"]
            )
            
            self.db.add(document)
            self.db.commit()
            self.db.refresh(document)
            
            return {
                "success": True,
                "message": "파일이 성공적으로 업로드되었습니다",
                "document_id": str(document.id),
                "file_url": upload_result["file_url"],
                "file_name": upload_result["original_filename"],
                "file_size": upload_result["file_size"],
                "document_type": document_type,
                "user_id": str(user_id)
            }
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"파일 업로드 중 오류가 발생했습니다: {str(e)}"
            )
    
    async def delete_file(self, user_id: str | uuid.UUID, document_type: str, file_name: str) -> dict:
        """파일 삭제 및 DB에서 레코드 제거"""
        try:
            uid = self._to_uuid(user_id)
            
            # 1. JobSeeker 존재 확인
            job_seeker = self.db.query(JobSeeker).filter(JobSeeker.user_id == uid).first()
            if not job_seeker:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="구직자 정보를 찾을 수 없습니다"
                )
            
            # 2. DB에서 문서 레코드 찾기
            document = self.db.query(JobSeekerDocument).filter(
                JobSeekerDocument.job_seeker_id == job_seeker.id,
                JobSeekerDocument.document_type == document_type,
                JobSeekerDocument.file_name == file_name
            ).first()
            
            if not document:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="파일을 찾을 수 없습니다"
                )
            
            # 3. 파일 경로 구성 (업로드할 때와 동일한 구조)
            file_path = f"uploads/{user_id}/{document_type}/{file_name}"
            
            # 4. 로컬 파일 시스템에서 파일 삭제
            delete_result = await self.s3_service.delete_file(file_path)
            
            if not delete_result["success"]:
                # 파일이 없어도 DB 레코드는 삭제 (정리 목적)
                logger.warning(f"파일 삭제 실패하지만 DB 레코드는 삭제: {delete_result['error']}")
            
            # 5. DB에서 레코드 삭제
            self.db.delete(document)
            self.db.commit()
            
            return {
                "success": True,
                "message": "파일이 성공적으로 삭제되었습니다",
                "deleted_file": {
                    "file_name": file_name,
                    "document_type": document_type,
                    "user_id": str(user_id)
                }
            }
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"파일 삭제 중 오류가 발생했습니다: {str(e)}"
            )
