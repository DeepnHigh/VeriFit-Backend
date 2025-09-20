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
import pandas as pd

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
        
        # 2. Big5 성격검사 결과 조회 - 최신 1건만
        big5_latest = self.db.query(Big5TestResult).filter(
            Big5TestResult.job_seeker_id == job_seeker.id
        ).order_by(Big5TestResult.test_date.desc()).first()
        
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
            'big5_test_results': [big5_latest] if big5_latest else [],
            'ai_learning_answers': ai_learning_answers,
            'documents': documents,
            'behavior_text': getattr(job_seeker, 'behavior_text', None)
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
            
            # 4. GitHub CSV 파일인 경우 파싱하여 github_repositories 업데이트
            github_data = None
            if document_type == "github" and upload_result["content_type"] in ["text/csv", "application/csv"]:
                github_data = await self._parse_github_csv(upload_result["file_path"])
                if github_data:
                    job_seeker.github_repositories = github_data
                    self.db.add(job_seeker)
                    self.db.commit()
                    self.db.refresh(job_seeker)
            
            return {
                "success": True,
                "message": "파일이 성공적으로 업로드되었습니다",
                "document_id": str(document.id),
                "file_url": upload_result["file_url"],
                "file_name": upload_result["original_filename"],
                "file_size": upload_result["file_size"],
                "document_type": document_type,
                "user_id": str(user_id),
                "github_data": github_data
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
            
            # 3. 실제 저장된 파일 경로 찾기 (UUID 파일명 사용)
            # DB에 저장된 file_url에서 실제 파일명 추출
            actual_file_path = None
            logger.info(f"🔍 삭제할 문서 정보 - file_url: {document.file_url}, file_name: {document.file_name}")
            
            if document.file_url:
                # file_url: http://localhost:8000/files/{user_id}/{document_type}/{uuid_filename}
                # 실제 파일 경로: uploads/{user_id}/{document_type}/{uuid_filename}
                url_parts = document.file_url.split('/')
                logger.info(f"🔍 URL 분할 결과: {url_parts}")
                if len(url_parts) >= 4:
                    uuid_filename = url_parts[-1]  # 마지막 부분이 실제 파일명
                    actual_file_path = f"uploads/{user_id}/{document_type}/{uuid_filename}"
                    logger.info(f"🔍 실제 파일 경로: {actual_file_path}")
                else:
                    logger.warning(f"⚠️ URL 형식이 예상과 다름: {document.file_url}")
            else:
                logger.warning(f"⚠️ file_url이 없음: {document.file_name}")
            
            # 4. 로컬 파일 시스템에서 파일 삭제
            delete_result = {"success": True, "message": "파일 삭제 건너뜀"}
            if actual_file_path:
                logger.info(f"🗑️ 파일 삭제 시도: {actual_file_path}")
                delete_result = await self.s3_service.delete_file(actual_file_path)
                if not delete_result["success"]:
                    # 파일이 없어도 DB 레코드는 삭제 (정리 목적)
                    logger.warning(f"파일 삭제 실패하지만 DB 레코드는 삭제: {delete_result['error']}")
                else:
                    logger.info(f"✅ 파일 삭제 성공: {actual_file_path}")
            else:
                logger.warning(f"실제 파일 경로를 찾을 수 없음. DB 레코드만 삭제: {document.file_url}")
            
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
    
    async def _parse_github_csv(self, file_path: str) -> dict:
        """GitHub CSV 파일을 pandas로 파싱하여 username과 repository URL 추출"""
        try:
            usernames = set()
            repositories = set()
            
            # pandas로 CSV 파일 읽기 (인코딩 자동 감지)
            try:
                # 여러 인코딩 시도
                encodings = ['utf-8', 'utf-8-sig', 'cp949', 'euc-kr', 'latin-1']
                df = None
                
                for encoding in encodings:
                    try:
                        df = pd.read_csv(file_path, encoding=encoding, header=None)
                        logger.info(f"📊 CSV 파일 인코딩 감지: {encoding}")
                        break
                    except UnicodeDecodeError:
                        continue
                    except Exception as e:
                        logger.warning(f"⚠️ {encoding} 인코딩 시도 중 오류: {e}")
                        continue
                
                if df is None:
                    logger.error("❌ 지원되는 인코딩을 찾을 수 없습니다")
                    return None
                
                logger.info(f"📊 CSV 파일 읽기 성공 - 행 수: {len(df)}, 열 수: {len(df.columns)}")
                
                # 최소 2개 컬럼이 있는지 확인
                if len(df.columns) < 2:
                    logger.error(f"❌ CSV 파일에 최소 2개 컬럼이 필요합니다. 현재: {len(df.columns)}개")
                    return None
                
                # 각 행 처리
                for index, row in df.iterrows():
                    if pd.notna(row.iloc[0]) and pd.notna(row.iloc[1]):
                        username = str(row.iloc[0]).strip()
                        repo_url = str(row.iloc[1]).strip()
                        
                        # username이 비어있지 않으면 추가
                        if username and username != 'nan':
                            usernames.add(username)
                        
                        # repository URL이 비어있지 않고 GitHub URL인지 확인
                        if repo_url and repo_url != 'nan' and ('github.com' in repo_url or repo_url.startswith('http')):
                            repositories.add(repo_url)
                    else:
                        logger.warning(f"⚠️ {index+1}행: 빈 값이 있습니다")
                
                logger.info(f"📊 GitHub CSV 파싱 완료 - 사용자: {len(usernames)}개, 저장소: {len(repositories)}개")
                logger.info(f"📊 사용자 목록: {list(usernames)}")
                logger.info(f"📊 저장소 목록: {list(repositories)}")
                
                return {
                    "username": list(usernames),
                    "repository": list(repositories)
                }
                
            except Exception as e:
                logger.error(f"❌ pandas CSV 읽기 실패: {e}")
                return None
            
        except Exception as e:
            logger.error(f"❌ GitHub CSV 파싱 실패: {e}")
            return None
