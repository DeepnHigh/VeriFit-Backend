from sqlalchemy.orm import Session
from app.models.applicant import Applicant

class ApplicantService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_applicant_profile(self, user_id: int):
        """지원자 마이페이지 정보 조회"""
        applicant = self.db.query(Applicant).filter(Applicant.user_id == user_id).first()
        if not applicant:
            return {"error": "지원자 정보를 찾을 수 없습니다"}
        
        return {
            "applicant": applicant,
            "documents": [],  # TODO: 문서 목록 구현
            "aptitude_tests": [],  # TODO: 적성검사 결과 구현
            "own_qnas": []  # TODO: AI QnA 구현
        }
    
    def create_bio(self, user_id: int, bio: str):
        """지원자 짧은소개 등록"""
        applicant = self.db.query(Applicant).filter(Applicant.user_id == user_id).first()
        if not applicant:
            # 새로 생성
            applicant = Applicant(user_id=user_id, bio=bio)
            self.db.add(applicant)
        else:
            applicant.bio = bio
        
        self.db.commit()
        return {"message": "짧은소개가 등록되었습니다", "bio": bio}
    
    def update_bio(self, user_id: int, bio: str):
        """지원자 짧은소개 수정"""
        return self.create_bio(user_id, bio)  # 동일한 로직
    
    def create_applicant_info(self, user_id: int, info_data: dict):
        """지원자 기본정보 등록"""
        applicant = self.db.query(Applicant).filter(Applicant.user_id == user_id).first()
        if not applicant:
            applicant = Applicant(user_id=user_id, **info_data)
            self.db.add(applicant)
        else:
            for key, value in info_data.items():
                setattr(applicant, key, value)
        
        self.db.commit()
        return {"message": "기본정보가 등록되었습니다"}
    
    def update_applicant_info(self, user_id: int, info_data: dict):
        """지원자 기본정보 수정"""
        return self.create_applicant_info(user_id, info_data)  # 동일한 로직
