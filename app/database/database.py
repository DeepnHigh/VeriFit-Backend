from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# SQLAlchemy 엔진 생성 (RDS 연결 슬롯 문제 해결을 위한 균형잡힌 설정)
engine = create_engine(
    settings.database_url,
    # 연결 풀 설정 (RDS 프리티어 균형잡힌 설정)
    pool_size=3,              # 기본 연결 풀 크기
    max_overflow=2,           # 추가 연결 허용
    pool_timeout=30,          # 연결 대기 시간 (30초)
    pool_recycle=300,         # 연결 재사용 시간 (5분)
    pool_pre_ping=True,       # 연결 유효성 검사
    echo=False                # SQL 쿼리 로깅
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
