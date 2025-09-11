from sqlalchemy.orm import Session, joinedload
from app.models.job_seeker import JobSeeker
from app.models.aptitude_test_result import AptitudeTestResult
from app.models.job_seeker_ai_learning_response import JobSeekerAILearningResponse
from app.models.ai_learning_question import AILearningQuestion
from app.models.job_seeker_document import JobSeekerDocument
import uuid

class JobSeekerService:
    def __init__(self, db: Session):
        self.db = db
    
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
        
        # 2. 적성검사 결과 조회
        aptitude_results = self.db.query(AptitudeTestResult).filter(
            AptitudeTestResult.job_seeker_id == job_seeker.id
        ).all()
        
        # 3. AI 학습 응답 조회 (질문 정보 포함)
        ai_responses = self.db.query(JobSeekerAILearningResponse).options(
            joinedload(JobSeekerAILearningResponse.question)
        ).filter(
            JobSeekerAILearningResponse.job_seeker_id == job_seeker.id
        ).all()
        
        # 4. 문서 조회
        documents = self.db.query(JobSeekerDocument).filter(
            JobSeekerDocument.job_seeker_id == job_seeker.id
        ).all()
        
        # 결과를 딕셔너리로 구성
        result = {
            'job_seeker': job_seeker,
            'aptitude_test_results': aptitude_results,
            'ai_learning_responses': ai_responses,
            'documents': documents
        }
        
        return result
