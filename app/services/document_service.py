from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException, status
import os
import uuid
from app.core.config import settings
from app.services.s3_service import S3Service
from app.models.job_seeker_document import JobSeekerDocument
from app.models.job_seeker import JobSeeker

class DocumentService:
    def __init__(self, db: Session):
        self.db = db
        self.s3_service = S3Service()
    
    async def upload_document(
        self, 
        user_id: str, 
        file: UploadFile, 
        document_type: str = "other"
    ):
        """문서 업로드 - S3 저장 및 DB 기록"""
        try:
            # 1. JobSeeker 존재 확인
            user_uuid = uuid.UUID(user_id)
            job_seeker = self.db.query(JobSeeker).filter(
                JobSeeker.user_id == user_uuid
            ).first()
            
            if not job_seeker:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="구직자 정보를 찾을 수 없습니다"
                )
            
            # 2. S3에 파일 업로드
            upload_result = await self.s3_service.upload_file(
                file=file,
                user_id=user_id,
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
                "document_type": document_type
            }
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"파일 업로드 중 오류가 발생했습니다: {str(e)}"
            )
    
    def get_document(self, document_id: int):
        """문서 다운로드"""
        # TODO: 실제 파일 조회 및 다운로드 로직 구현
        return {
            "document_id": document_id,
            "message": "문서를 조회했습니다"
        }
    
    def delete_document(self, document_id: int):
        """문서 삭제"""
        # TODO: 실제 파일 삭제 로직 구현
        return {
            "message": "문서가 삭제되었습니다",
            "document_id": document_id
        }
