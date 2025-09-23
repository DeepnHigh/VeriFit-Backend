from pydantic_settings import BaseSettings
from typing import Optional, List
from pydantic import Field, model_validator
from typing import Optional
import json

class Settings(BaseSettings):
    
    # API 설정
    api_base_url: str = Field(default="http://localhost:8000", alias="API_BASE_URL")
    
    # 데이터베이스 설정
    database_url: str = Field(default="postgresql://verifit_master:verifit123@verifit-db.cpk0oamsu0g6.us-west-1.rds.amazonaws.com:5432/verifit_db", alias="DATABASE_URL")
    
    # JWT 설정
    secret_key: str = Field(default="your-secret-key-here", alias="SECRET_KEY")
    algorithm: str = Field(default="HS256", alias="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # 파일 업로드 설정
    upload_dir: str = Field(default="uploads", alias="UPLOAD_DIR")
    max_file_size: int = Field(default=10 * 1024 * 1024, alias="MAX_FILE_SIZE")  # 10MB
    
    # CORS 설정
    cors_origins: List[str] = Field(default=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://192.168.0.21:3000",
        "http://14.39.95.228:3000"
    ], alias="CORS_ORIGINS")

    # AWS S3 설정 (URL 기반)
    s3_base_url: str = Field(default="https://seoul-ht-01.s3.us-west-1.amazonaws.com/job_seeker_documents/", alias="S3_BASE_URL")
    
    # Mathpix API 설정
    mathpix_app_id: Optional[str] = Field(default=None, alias="MATHPIX_APP_ID")
    mathpix_app_key: Optional[str] = Field(default=None, alias="MATHPIX_APP_KEY")
    
    # AWS Bedrock 설정
    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")
    bedrock_model_id: str = Field(default="anthropic.claude-3-5-sonnet-20241022-v2:0", alias="BEDROCK_MODEL_ID")
    aws_bearer_token_bedrock: Optional[str] = Field(default=None, alias="AWS_BEARER_TOKEN_BEDROCK")
    
    # AWS Lambda 설정
    lambda_function_name: str = Field(default="basic_info_extraction", alias="LAMBDA_FUNCTION_NAME")

    # 선택: Lambda Function URL 호출 지원
    lambda_function_url: Optional[str] = Field(default=None, alias="LAMBDA_FUNCTION_URL")
    # Function URL 인증 방식: NONE 또는 AWS_IAM
    lambda_function_url_auth: Optional[str] = Field(default="NONE", alias="LAMBDA_FUNCTION_URL_AUTH")

    # 면접 질문 생성용 별도 Lambda 설정 (기존 기능과 분리)
    lambda_questions_function_name: str = Field(default="verifit-generate-questions", alias="LAMBDA_QUESTIONS_FUNCTION_NAME")
    lambda_questions_function_url: Optional[str] = Field(default=None, alias="LAMBDA_QUESTIONS_FUNCTION_URL")

    # 지원자 평가용 별도 Lambda 설정 (향후 사용)
    lambda_evaluation_function_name: str = Field(default="verifit-evaluate-candidate", alias="LAMBDA_EVALUATION_FUNCTION_NAME")
    lambda_evaluation_function_url: Optional[str] = Field(default=None, alias="LAMBDA_EVALUATION_FUNCTION_URL")

    # KB 인덱싱용 별도 Lambda 설정
    lambda_kb_ingest_function_name: str = Field(default="verifit-kb-ingest", alias="LAMBDA_KB_INGEST_FUNCTION_NAME")
    lambda_kb_ingest_function_url: Optional[str] = Field(default=None, alias="LAMBDA_KB_INGEST_FUNCTION_URL")

    # GitHub Token (권장: .env 또는 환경변수로 설정)
    github_token: Optional[str] = Field(default=None, alias="GITHUB_TOKEN")


    @model_validator(mode="after")
    def _normalize_cors_origins(self):
        """환경변수로 전달된 CORS_ORIGINS가 문자열(JSON)일 경우 리스트로 파싱"""
        origins = self.cors_origins
        if isinstance(origins, str):
            try:
                parsed = json.loads(origins)
                if isinstance(parsed, list):
                    self.cors_origins = parsed
            except Exception:
                # 쉼표 구분 문자열일 수도 있으니 분리 시도
                self.cors_origins = [o.strip() for o in origins.split(",") if o.strip()]
        return self

    
    # pydantic v2 model configuration: load `.env` and ignore extra env vars
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

settings = Settings()
