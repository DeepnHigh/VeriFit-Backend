# RDS PostgreSQL 연결 문제 해결

## 🔍 현재 상황 분석

### ✅ 확인된 사항
- DNS 해석: 정상 (13.52.206.81)
- 보안 그룹: default (모든 포트 열림)
- RDS 인스턴스: 생성 완료

### ❌ 문제점
- ping 실패 (100% packet loss)
- PostgreSQL 연결 타임아웃

## 🚨 가능한 원인들

### 1. **RDS 인스턴스 상태**
- 인스턴스가 아직 시작 중일 수 있음
- 인스턴스가 중지된 상태일 수 있음

### 2. **VPC 설정 문제**
- RDS가 Private Subnet에 있을 수 있음
- Route Table 설정 문제

### 3. **퍼블릭 액세스 설정**
- RDS 인스턴스의 "Publicly accessible" 설정이 No일 수 있음

### 4. **네트워크 ACL**
- VPC의 Network ACL에서 차단

## 🔧 해결 방법

### 1. **AWS 콘솔에서 확인할 사항**

#### RDS 인스턴스 상태
```
RDS → Databases → verifit-db
- Status: Available (녹색)
- Publicly accessible: Yes
```

#### VPC 설정
```
RDS → Databases → verifit-db → Connectivity & security
- VPC: vpc-xxxxx
- Subnet group: default
- Publicly accessible: Yes
```

#### 보안 그룹 상세
```
EC2 → Security Groups → default
- Inbound rules: All traffic, All protocols, All ports, 0.0.0.0/0
```

### 2. **RDS 인스턴스 재시작**
만약 인스턴스가 중지된 상태라면:
```
RDS → Databases → verifit-db → Actions → Reboot
```

### 3. **퍼블릭 액세스 활성화**
```
RDS → Databases → verifit-db → Modify
- Publicly accessible: Yes
- Apply immediately: Yes
```

## 🧪 연결 테스트 명령어

### 1. **기본 연결 테스트**
```bash
telnet verifit-db.cpk0oamsu0g6.us-west-1.rds.amazonaws.com 5432
```

### 2. **PostgreSQL 클라이언트 테스트**
```bash
psql -h verifit-db.cpk0oamsu0g6.us-west-1.rds.amazonaws.com -p 5432 -U verifit_master -d verifit-db
```

### 3. **Python 연결 테스트**
```bash
python -c "
import psycopg2
try:
    conn = psycopg2.connect(
        host='verifit-db.cpk0oamsu0g6.us-west-1.rds.amazonaws.com',
        port=5432,
        database='verifit-db',
        user='verifit_master',
        password='verifit123'
    )
    print('✅ PostgreSQL 연결 성공!')
    conn.close()
except Exception as e:
    print(f'❌ 연결 실패: {e}')
"
```

## 💡 임시 해결책

RDS 연결이 해결될 때까지 로컬 개발을 계속 진행:

```python
# app/core/config.py
database_url: str = "sqlite:///./verifit.db"  # 로컬 개발용
```

## 📋 체크리스트

- [ ] RDS 인스턴스 상태: Available
- [ ] Publicly accessible: Yes
- [ ] 보안 그룹: 모든 포트 열림
- [ ] VPC: default VPC 사용
- [ ] Subnet: public subnet 사용

