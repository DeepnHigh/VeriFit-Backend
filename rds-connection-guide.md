# RDS PostgreSQL 연결 가이드

## 🔧 RDS 연결 정보
- **엔드포인트**: verifit-db.cpk0oamsu0g6.us-west-1.rds.amazonaws.com
- **포트**: 5432
- **데이터베이스**: verifit_db
- **사용자명**: verifit_master
- **비밀번호**: verifit123
- **리전**: us-west-1 (캘리포니아)

## ❌ 현재 문제: Connection Timeout

연결이 타임아웃되는 이유는 보안 그룹 설정 문제일 가능성이 높습니다.

## 🔍 해결 방법

### 1. 보안 그룹 확인 및 수정

AWS 콘솔에서 다음을 확인하세요:

1. **RDS 인스턴스** → **Connectivity & security** 탭
2. **VPC security groups** 클릭
3. **Inbound rules** 확인

### 2. 보안 그룹 규칙 추가

다음 규칙을 추가해야 합니다:

```
Type: PostgreSQL
Protocol: TCP
Port: 5432
Source: 0.0.0.0/0 (또는 특정 IP)
```

### 3. 퍼블릭 액세스 확인

RDS 인스턴스 설정에서:
- **Publicly accessible**: Yes
- **VPC security groups**: 올바른 보안 그룹 선택

## 🧪 연결 테스트

보안 그룹 수정 후 다음 명령어로 테스트:

```bash
# 1. 환경 변수 설정
export DATABASE_URL="postgresql://verifit_master:verifit123@verifit-db.cpk0oamsu0g6.us-west-1.rds.amazonaws.com:5432/verifit-db"

# 2. 연결 테스트
python -c "from app.database.database import engine; conn = engine.connect(); print('RDS 연결 성공!'); conn.close()"
```

## 📝 설정 파일 업데이트

연결 성공 후 `app/core/config.py`에서:

```python
database_url: str = "postgresql://verifit_master:verifit123@verifit-db.cpk0oamsu0g6.us-west-1.rds.amazonaws.com:5432/verifit-db"
```

## 🚀 다음 단계

1. 보안 그룹 수정
2. RDS 연결 테스트
3. 데이터베이스 테이블 생성
4. pgvector 확장 활성화 (AI 서비스용)

## 💡 참고사항

- 해커톤 규칙에 따라 퍼블릭 액세스가 허용되어야 합니다
- 보안 그룹에서 포트 5432가 열려있어야 합니다
- RDS 인스턴스가 실행 중인지 확인하세요

