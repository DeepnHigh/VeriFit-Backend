from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate
from app.core.security import get_password_hash, verify_password

class AuthService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_by_email(self, email: str) -> User:
        """이메일로 사용자 조회"""
        return self.db.query(User).filter(User.email == email).first()
    
    def authenticate_user(self, email: str, password: str) -> User:
        """사용자 인증"""
        user = self.get_user_by_email(email)
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user
    
    def create_user(self, user_data: UserCreate) -> User:
        """새 사용자 생성"""
        hashed_password = get_password_hash(user_data.password)
        db_user = User(
            email=user_data.email,
            password_hash=hashed_password,
            name=user_data.name,
            user_type=user_data.user_type
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user
