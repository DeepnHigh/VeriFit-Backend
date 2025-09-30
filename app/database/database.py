from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import os

# 풀 설정을 환경변수로 조정 가능하도록 확장
# (기본값은 기존보다 여유 있게 상향하여 AI 평가 중 동시 폴링/요청으로 인한 Timeout 완화)
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))          # 기존 3 -> 5
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))    # 기존 2 -> 5
POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))   # 그대로 기본 유지
POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "300"))  # 5분

engine = create_engine(
    settings.database_url,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT,
    pool_recycle=POOL_RECYCLE,
    pool_pre_ping=True,
    echo=False
)

# 세션 팩토리 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base 클래스 생성 (모든 모델이 상속받을 클래스)
Base = declarative_base()

# 데이터베이스 세션 의존성
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 데이터베이스 연결 상태 확인
def check_db_connection():
    """데이터베이스 연결 상태를 확인합니다"""
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            # 간단한 쿼리로 연결 테스트
            result = conn.execute(text("SELECT 1"))
            return {"status": "connected", "message": "데이터베이스 연결 성공"}
    except Exception as e:
        return {"status": "error", "message": f"데이터베이스 연결 실패: {str(e)}"}

# 연결 풀 상태 확인
def get_pool_status():
    """현재 연결 풀 상태를 확인합니다"""
    pool = engine.pool
    return {
        "pool_size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "total_connections": pool.size() + pool.overflow()
    }

# 연결 풀 강제 정리
def dispose_pool():
    """연결 풀의 모든 연결을 강제로 해제합니다"""
    try:
        engine.dispose()
        return {"status": "success", "message": "연결 풀이 정리되었습니다"}
    except Exception as e:
        return {"status": "error", "message": f"연결 풀 정리 실패: {str(e)}"}
