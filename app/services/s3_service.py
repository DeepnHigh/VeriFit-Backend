import uuid
import aiohttp
from datetime import datetime
from fastapi import UploadFile
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)
class S3Service:
    def __init__(self):
        self.s3_base_url = settings.s3_base_url

    async def upload_file(
        self,
        file: UploadFile,
        user_id: str,
        document_type: str,
    ) -> dict:
        """
        로컬 파일 시스템에 파일 업로드 (임시 해결책)
        
        Args:
            file: 업로드할 파일
            user_id: 사용자 ID
            document_type: 문서 타입 (resume, portfolio, certificate 등)
            
        Returns:
            dict: 업로드 결과 정보
        """
        try:
            import os
            from app.core.config import settings

            # 파일 확장자 추출
            file_extension = ""
            if file.filename and "." in file.filename:
                file_extension = file.filename.split(".")[-1]
            
            # 고유 파일명 생성
            unique_filename = f"{uuid.uuid4()}.{file_extension}" if file_extension else str(uuid.uuid4())
            
            # 로컬 저장 경로 생성: uploads/{user_id}/{document_type}/{unique_filename}
            upload_dir = f"{settings.upload_dir}/{user_id}/{document_type}"
            os.makedirs(upload_dir, exist_ok=True)
            
            file_path = f"{upload_dir}/{unique_filename}"
            
            # 파일 내용 읽기
            file_content = await file.read()
            
            # 로컬 파일 시스템에 저장
            with open(file_path, "wb") as f:
                f.write(file_content)
            
            # 파일 포인터를 처음으로 되돌리기
            await file.seek(0)
            
            # URL 생성 (로컬 서버 기준)
            from app.core.config import settings
            file_url = f"{settings.api_base_url}/files/{user_id}/{document_type}/{unique_filename}"
            
            return {
                "success": True,
                "file_url": file_url,
                "file_path": file_path,
                "original_filename": file.filename,
                "file_size": len(file_content),
                "content_type": file.content_type,
                "document_type": document_type,
                "user_id": user_id
            }
            
        except Exception as e:
            logger.error(f"파일 업로드 오류: {e}")
            return {
                "success": False,
                "error": f"파일 업로드 실패: {str(e)}"
            }
    
    async def delete_file(self, file_path: str) -> dict:
        """
        로컬 파일 시스템에서 파일 삭제
        
        Args:
            file_path: 삭제할 파일의 경로 (uploads/{user_id}/{document_type}/{filename})
            
        Returns:
            dict: 삭제 결과
        """
        try:
            import os
            
            # 파일이 존재하는지 확인
            if not os.path.exists(file_path):
                return {
                    "success": False,
                    "error": f"파일을 찾을 수 없습니다: {file_path}"
                }
            
            # 파일 삭제
            os.remove(file_path)
            
            return {
                "success": True,
                "message": f"파일이 삭제되었습니다: {file_path}"
            }
                        
        except Exception as e:
            logger.error(f"파일 삭제 오류: {e}")
            return {
                "success": False,
                "error": f"파일 삭제 실패: {str(e)}"
            }
    
    def get_file_url(self, file_path: str) -> str:
        """
        파일 다운로드 URL 생성 (로컬 파일 시스템용)
        
        Args:
            file_path: 파일 경로 (uploads/{user_id}/{document_type}/{filename})
            
        Returns:
            str: 파일 다운로드 URL
        """
        # uploads/ 경로를 /files/로 변경하여 로컬 서버 URL 생성
        if file_path.startswith("uploads/"):
            relative_path = file_path.replace("uploads/", "")
            return f"http://localhost:8000/files/{relative_path}"
        return f"http://localhost:8000/files/{file_path}"
