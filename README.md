# VeriFit Backend API

AI 기반 채용 플랫폼의 백엔드 API 서버입니다.

## 기술 스택

- **FastAPI**: Python 웹 프레임워크
- **SQLAlchemy**: ORM
- **PostgreSQL**: 데이터베이스 (RDS PostgreSQL)
- **JWT**: 인증
- **Pydantic**: 데이터 검증
- **AWS**: RDS, EC2, S3, Lambda
## 프로젝트 구조

```
app/
├── core/           # 핵심 설정 및 유틸리티
├── database/       # 데이터베이스 설정
├── models/         # SQLAlchemy 모델 (Entity)
├── schemas/        # Pydantic 스키마 (DTO)
├── services/       # 비즈니스 로직 (Service)
└── routers/        # API 라우터 (Controller)
```

## 설치 및 실행

1. conda 가상환경 생성 및 활성화:
```bash
conda create -n verifit python=3.11 -y
conda activate verifit
```

2. 의존성 설치:
```bash
pip install -r requirements.txt
```

3. 환경 변수 설정:
```bash
cp .env.example .env
# .env 파일을 편집하여 실제 값으로 변경
```

4. 데이터베이스 설정:
```bash
# PostgreSQL 데이터베이스 생성
createdb verifit_db
```

5. 서버 실행:
```bash
python run.py
```

API 문서는 http://localhost:8000/docs 에서 확인할 수 있습니다.

## API 엔드포인트

### 인증
- `POST /api/login` - 로그인
- `POST /api/register` - 회원가입

### 지원자
- `GET /api/applicants/{user_id}` - 지원자 마이페이지
- `POST /api/applicants/bio/{user_id}` - 짧은소개 등록
- `PUT /api/applicants/bio/{user_id}` - 짧은소개 수정

### 채용공고
- `GET /api/job-postings` - 채용공고 목록
- `POST /api/job-postings` - 채용공고 생성

### 면접
- `POST /api/interviews/{job_posting_id}` - 면접 및 리포트 생성
- `GET /api/interviews/{job_posting_id}` - 채용현황 조회

### 문서
- `POST /api/docs/{user_id}` - 파일 업로드
- `GET /api/docs/{document_id}` - 파일 다운로드
