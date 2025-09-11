from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import (
    job_seekers, job_postings, interviews, auth, documents,
    aptitude_tests, behavior_tests, ai_learning
)
from app.database.database import engine, Base

# 모든 모델 import (테이블 생성을 위해 필요)
from app.models import (
    user, job_seeker, company, job_posting, application,
    ai_evaluation, ai_interview_message, ai_learning_question, 
    ai_overall_report, aptitude_test_result, evaluation_criteria,
    job_seeker_ai_agent, job_seeker_ai_learning_response, job_seeker_document
)

# 데이터베이스 테이블 생성
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="VeriFit API",
    description="AI 기반 채용 플랫폼 백엔드 API",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js 개발 서버
        "http://localhost:3001",  # Next.js 대체 포트
        "http://127.0.0.1:3000",  # 로컬호스트 대체
        "http://127.0.0.1:3001",  # 로컬호스트 대체
        "http://192.168.0.21:3000",  # 네트워크 IP
        "http://192.168.0.21:3001"   # 네트워크 IP 대체 포트
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(auth.router, tags=["인증"])
app.include_router(job_seekers.router, tags=["구직자"])
app.include_router(job_postings.router, tags=["채용공고"])
app.include_router(interviews.router, tags=["면접"])
app.include_router(documents.router, tags=["문서"])
app.include_router(aptitude_tests.router, tags=["적성검사"])
app.include_router(behavior_tests.router, tags=["행동검사"])
app.include_router(ai_learning.router, tags=["AI학습"])

@app.get("/")
async def root():
    return {"message": "VeriFit API 서버가 실행 중입니다!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/db-status")
async def database_status():
    """데이터베이스 연결 및 테이블 상태 확인"""
    try:
        from sqlalchemy import text
        from app.database.database import engine
        
        # 연결 테스트
        with engine.connect() as conn:
            # 테이블 목록 조회
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """))
            tables = [row[0] for row in result.fetchall()]
            
            # 각 테이블의 레코드 수 확인
            table_counts = {}
            for table in tables:
                count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                table_counts[table] = count_result.scalar()
            
            return {
                "status": "connected",
                "database": "RDS PostgreSQL",
                "tables": tables,
                "table_counts": table_counts,
                "total_tables": len(tables)
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

