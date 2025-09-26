## VeriFit Backend API (업데이트)

AI 기반 채용/평가 플랫폼의 FastAPI 백엔드입니다.

### 주요 역할
- 사용자/기업 인증 및 권한
- 채용공고 / 지원 / 면접 상태 관리
- AI 평가 결과/리포트 저장 (하드/소프트 스킬, Big5, 행동검사 등)
- 파일 업로드 (문서 저장 및 S3 / 로컬)
- Lambda / Bedrock 연계 (질문 생성, 평가, 개인정보 추출 등)

### 기술 스택
FastAPI · SQLAlchemy 2.x · PostgreSQL (RDS) · Alembic · Pydantic v2 · JWT · boto3 · PM2 배포

### 디렉토리 구조
```
app/
├─ core/            # 설정, 보안, 환경
├─ database/        # 세션/엔진/풀 관리
├─ models/          # SQLAlchemy 모델
├─ schemas/         # Pydantic DTO
├─ services/        # 비즈니스 로직
├─ routers/         # API 엔드포인트
└─ utils, ...
uploads/            # 업로드 파일 (StaticFiles)
```

### 빠른 실행 (개발)
```bash
conda create -n verifit python=3.11 -y
conda activate verifit
pip install -r requirements.txt
cp .env .env.local  # 또는 새로 작성 (예: DATABASE_URL 등)
python run.py
```
Swagger/OpenAPI: http://localhost:8000/docs

### 핵심 환경 변수 (예시)
```
DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/verifit_db
CORS_ORIGINS=["http://localhost:3000"]
JWT_SECRET=change_me
JWT_ALGORITHM=HS256
AWS_REGION=us-west-1
LAMBDA_QUESTIONS_FUNCTION_URL=...
LAMBDA_EVALUATION_FUNCTION_URL=...
```

### 실행 (PM2 / 프로덕션)
`ecosystem.config.js` 사용:
```bash
pm2 start ecosystem.config.js
pm2 restart verifit-backend
pm2 logs verifit-backend
```

### 헬스/모니터링 엔드포인트
| Path | 설명 |
|------|------|
| `/health` | 단순 헬스 체크 |
| `/pool-status` | 커넥션 풀 상태 |
| `/db-status` | 테이블/카운트 상태 |
| `/debug-db/{user_id}` | 특정 사용자 디버그 |

### 인터뷰 & 평가 관련 흐름 (요약)
1. 기업이 채용공고 생성 (평가 스킬 세트 포함)
2. 지원자 지원 → application 생성
3. 면접/AI 처리 트리거 (`POST /api/interviews/{job_posting_id}`)
4. Lambda/Bedrock 통해 질문 생성 및 평가
5. 결과 저장: ai_evaluation, ai_interview_message, ai_overall_report 등
6. 프론트: 채용현황/리포트 페이지 조회 (`GET /api/interviews/{job_posting_id}`)

### 주요 라우터 (요약)
- 인증: `/api/login`, `/api/register`
- 채용공고: `/api/job-postings`
- 인터뷰: `/api/interviews/{job_posting_id}`
- 지원: `/api/applications/*`
- 문서: `/api/docs/*`
- Big5/행동검사: `/api/big5-tests/*`, `/api/behavior-tests/*`

### Lambda 배포 (요약)
스크립트: `deploy_lambda.py`
1. `lambda_requirements.txt` 기반 패키징
2. Bedrock / 개인정보 추출 / 질문생성 등 Lambda 핸들러 zip 생성
3. IAM Role 준비 후 `deploy_lambda()` 활성화하여 실제 배포

### 데이터베이스 마이그레이션
Alembic 설정이 있다면 (migrations 디렉토리) 다음 패턴 사용:
```bash
alembic revision -m "message"
alembic upgrade head
```

### 개발 메모
- CORS 이중 처리: 표준 미들웨어 + fallback 미들웨어 (에러 시에도 헤더 유지)
- 풀 모니터링: 커넥션 누수/과사용 추적 가능 (`/pool-status`)
- 정적 파일: `/files/*` 로 서빙

### 향후 개선 아이디어
- rate limiting / audit log
- 캐싱 (Redis) 도입 검토
- 평가 결과 버전 기록 테이블 분리

MIT License
