from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.routers import (
    job_seekers, job_postings, interviews, auth, documents,
    big5_tests, behavior_tests, ai_learning
)
from app.database.database import engine, Base

# 모든 모델 import (테이블 생성을 위해 필요)
from app.models import (
    user, job_seeker, company, job_posting, application,
    ai_evaluation, ai_interview_message, ai_learning_question, 
    ai_overall_report, big5_test_result, evaluation_criteria,
    job_seeker_ai_agent, job_seeker_ai_learning_response, job_seeker_document
)

# 데이터베이스 테이블 생성
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="VeriFit API",
    description="AI 기반 채용 플랫폼 백엔드 API",
    version="1.0.0"
)

# CORS 설정 (개발 환경용 - 모든 origin 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 환경에서 모든 origin 허용
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
app.include_router(big5_tests.router, tags=["Big5성격검사"])
app.include_router(behavior_tests.router, tags=["행동검사"])
app.include_router(ai_learning.router, tags=["AI학습"])

# 정적 파일 서빙 (업로드된 파일들)
app.mount("/files", StaticFiles(directory="uploads"), name="files")

@app.get("/")
async def root():
    return {"message": "VeriFit API 서버가 실행 중입니다!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/pool-status")
async def pool_status():
    """데이터베이스 연결 풀 상태 확인"""
    try:
        from app.database.database import get_pool_status, check_db_connection
        
        connection_status = check_db_connection()
        pool_status = get_pool_status()
        
        return {
            "connection_status": connection_status,
            "pool_status": pool_status,
            "recommendations": {
                "high_overflow": "연결 풀 오버플로우가 높습니다. pool_size를 늘리거나 max_overflow를 조정하세요.",
                "many_invalid": "무효한 연결이 많습니다. pool_recycle 시간을 줄이거나 네트워크 상태를 확인하세요.",
                "all_checked_out": "모든 연결이 사용 중입니다. pool_size를 늘리거나 애플리케이션의 연결 사용 패턴을 확인하세요."
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@app.post("/dispose-pool")
async def dispose_connection_pool():
    """데이터베이스 연결 풀 강제 정리"""
    try:
        from app.database.database import dispose_pool
        
        result = dispose_pool()
        return result
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@app.get("/db-status")
async def database_status():
    """데이터베이스 연결 및 테이블 상태 확인"""
    try:
        from sqlalchemy import text
        from app.database.database import engine, check_db_connection, get_pool_status
        
        # 연결 테스트
        connection_status = check_db_connection()
        pool_status = get_pool_status()
        
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
                "connection_status": connection_status,
                "pool_status": pool_status,
                "tables": tables,
                "table_counts": table_counts,
                "total_tables": len(tables)
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@app.get("/debug-db/{user_id}")
async def debug_database(user_id: str):
    """디버깅용: 데이터베이스 직접 조회"""
    try:
        from sqlalchemy import text
        from app.database.database import engine
        import uuid
        
        # UUID 변환
        uid = uuid.UUID(user_id)
        
        with engine.connect() as conn:
            # job_seekers 테이블에서 해당 user_id 조회
            result = conn.execute(text("""
                SELECT id, user_id, full_name, email 
                FROM job_seekers 
                WHERE user_id = :user_id
            """), {"user_id": str(uid)})
            
            job_seeker = result.fetchone()
            
            # 모든 job_seekers 조회
            all_result = conn.execute(text("""
                SELECT id, user_id, full_name, email 
                FROM job_seekers 
                LIMIT 10
            """))
            
            all_job_seekers = [dict(row._mapping) for row in all_result.fetchall()]
        
        return {
            "input_user_id": user_id,
            "converted_uuid": str(uid),
            "found_job_seeker": dict(job_seeker._mapping) if job_seeker else None,
            "all_job_seekers": all_job_seekers
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "input_user_id": user_id
        }

@app.delete("/admin/clear-documents")
async def clear_all_documents():
    """관리자용: 모든 job_seeker_documents 데이터 삭제"""
    try:
        from sqlalchemy import text
        from app.database.database import engine
        
        with engine.connect() as conn:
            # 삭제 전 개수 확인
            count_result = conn.execute(text("SELECT COUNT(*) FROM job_seeker_documents"))
            before_count = count_result.scalar()
            
            # 모든 job_seeker_documents 삭제
            conn.execute(text("DELETE FROM job_seeker_documents"))
            conn.commit()
            
            # 삭제 후 개수 확인
            count_result = conn.execute(text("SELECT COUNT(*) FROM job_seeker_documents"))
            after_count = count_result.scalar()
        
        return {
            "success": True,
            "message": "모든 job_seeker_documents 데이터가 삭제되었습니다",
            "deleted_count": before_count,
            "remaining_count": after_count
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

