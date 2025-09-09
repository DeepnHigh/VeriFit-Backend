from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # 데이터베이스 설정
    # 개발용: SQLite, 프로덕션용: RDS PostgreSQL (해커톤 규칙)
    database_url: str = "sqlite:///./verifit.db"
    # RDS PostgreSQL 예시: "postgresql://username:password@rds-endpoint.region.rds.amazonaws.com:5432/verifit_db"
    
    # JWT 설정
    secret_key: str = "your-secret-key-here"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # 파일 업로드 설정
    upload_dir: str = "uploads"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    
    class Config:
        env_file = ".env"

settings = Settings()
