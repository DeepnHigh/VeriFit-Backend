from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # 데이터베이스 설정
    # 개발용: SQLite, 프로덕션용: RDS PostgreSQL (해커톤 규칙)
    # database_url: str = "sqlite:///./verifit.db"
    database_url: str = "postgresql://verifit_master:verifit123@verifit-db.cpk0oamsu0g6.us-west-1.rds.amazonaws.com:5432/verifit_db"
    # RDS PostgreSQL 예시: "postgresql://username:password@rds-endpoint.region.rds.amazonaws.com:5432/verifit_db"
    
    # JWT 설정
    secret_key: str = "your-secret-key-here"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # 파일 업로드 설정
    upload_dir: str = "uploads"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    
    # AWS S3 설정 (URL 기반)
    s3_base_url: str = "https://seoul-ht-01.s3.us-west-1.amazonaws.com/job_seeker_documents/"
    
    class Config:
        env_file = ".env"

settings = Settings()
