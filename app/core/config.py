from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional

class Settings(BaseSettings):
    # 데이터베이스 설정
    database_url: str = Field(default="postgresql://verifit_master:verifit123@verifit-db.cpk0oamsu0g6.us-west-1.rds.amazonaws.com:5432/verifit_db", alias="DATABASE_URL")
    
    # JWT 설정
    secret_key: str = Field(default="your-secret-key-here", alias="SECRET_KEY")
    algorithm: str = Field(default="HS256", alias="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # 파일 업로드 설정
    upload_dir: str = Field(default="uploads", alias="UPLOAD_DIR")
    max_file_size: int = Field(default=10 * 1024 * 1024, alias="MAX_FILE_SIZE")  # 10MB
    
    # AWS S3 설정 (URL 기반)
    s3_base_url: str = Field(default="https://seoul-ht-01.s3.us-west-1.amazonaws.com/job_seeker_documents/", alias="S3_BASE_URL")
    
    # Mathpix API 설정
    mathpix_app_id: Optional[str] = Field(default=None, alias="MATHPIX_APP_ID")
    mathpix_app_key: Optional[str] = Field(default=None, alias="MATHPIX_APP_KEY")
    
    # AWS Bedrock 설정
    aws_region: str = Field(default="us-west-1", alias="AWS_REGION")
    bedrock_model_id: str = Field(default="anthropic.claude-3-5-sonnet-20241022-v2:0", alias="BEDROCK_MODEL_ID")
    aws_bearer_token_bedrock: Optional[str] = Field(default=None, alias="AWS_BEARER_TOKEN_BEDROCK")
    
    # AWS Lambda 설정
    lambda_function_name: str = Field(default="basic_info_extraction", alias="LAMBDA_FUNCTION_NAME")
    
    # API 베이스 URL 설정
    api_base_url: str = Field(default="http://localhost:8000", alias="API_BASE_URL")
    
    # CORS 설정
    cors_origins: list = Field(default=["*"], alias="CORS_ORIGINS")
    
    class Config:
        env_file = ".env"

settings = Settings()
