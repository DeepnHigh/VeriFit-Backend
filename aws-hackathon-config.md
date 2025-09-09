# 해커톤 AWS 설정 가이드

## 🎯 해커톤 규칙에 따른 VeriFit 백엔드 설정

### 📋 사용 가능한 AWS 서비스
- ✅ Cloud9, EC2, Lambda, RDS, DynamoDB, S3, API GW, Amplify, SQS, SNS
- ❌ Aurora, Cognito, Route 53, Load Balancer, Auto Scaling 등

### 🗄️ 데이터베이스 설정

#### RDS PostgreSQL (프로덕션)
```bash
# 해커톤 규칙
- 엔진: PostgreSQL
- 템플릿: 프리티어
- 퍼블릭 액세스: 허용
- EC2 연결: X
- 리전: us-west-1 (캘리포니아)
```

#### 환경 변수 설정
```bash
# .env 파일
DATABASE_URL=postgresql://username:password@rds-endpoint.us-west-1.rds.amazonaws.com:5432/verifit_db
```

### 🔧 AI 서비스 확장 계획

#### 1. 벡터 검색 (pgvector 확장)
```sql
-- RDS PostgreSQL에서 pgvector 확장 활성화
CREATE EXTENSION IF NOT EXISTS vector;

-- 임베딩 저장 테이블
CREATE TABLE document_embeddings (
    id SERIAL PRIMARY KEY,
    document_id INTEGER,
    embedding vector(1536),  -- OpenAI embedding dimension
    content TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 유사성 검색 인덱스
CREATE INDEX ON document_embeddings USING ivfflat (embedding vector_cosine_ops);
```

#### 2. AI 서비스 아키텍처
```
FastAPI (EC2) → RDS PostgreSQL (벡터 + 관계형 데이터)
     ↓
Lambda (AI 처리) → S3 (파일 저장)
     ↓
Bedrock (AI 모델) - us-east-1, us-west-2, us-west-1
```

### 🚀 배포 전략

#### 개발 환경
- 로컬: SQLite
- conda 환경: verifit

#### 프로덕션 환경
- EC2: t3.medium (FastAPI 서버)
- RDS: PostgreSQL 프리티어 (데이터베이스)
- S3: {username}-verifit-files (파일 저장)
- Lambda: AI 처리 함수

### 📝 다음 단계

1. **RDS PostgreSQL 생성**
   - 프리티어 템플릿
   - pgvector 확장 활성화
   - 퍼블릭 액세스 허용

2. **EC2 인스턴스 설정**
   - t3.medium 타입
   - SafeInstanceProfileForUser-{username} 역할
   - FastAPI 서버 배포

3. **S3 버킷 생성**
   - 버킷명: {username}-verifit-files
   - 파일 업로드/다운로드 기능

4. **Lambda 함수 생성**
   - SafeRoleForUser-{username} 역할
   - AI 처리 로직 구현
