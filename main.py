from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import applicants, job_postings, interviews, auth, documents
from app.database.database import engine, Base

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
    allow_origins=["http://localhost:3000"],  # Next.js 개발 서버
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(auth.router, prefix="/api", tags=["인증"])
app.include_router(applicants.router, prefix="/api", tags=["지원자"])
app.include_router(job_postings.router, prefix="/api", tags=["채용공고"])
app.include_router(interviews.router, prefix="/api", tags=["면접"])
app.include_router(documents.router, prefix="/api", tags=["문서"])

@app.get("/")
async def root():
    return {"message": "VeriFit API 서버가 실행 중입니다!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
