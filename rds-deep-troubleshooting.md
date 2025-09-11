# RDS PostgreSQL 심층 문제 해결

## 🔍 진단 결과

### ✅ 정상 작동
- DNS 해석: `verifit-db.cpk0oamsu0g6.us-west-1.rds.amazonaws.com` → `13.52.206.81`
- 네트워크 경로: 정상

### ❌ 문제점
- 소켓 연결 실패 (에러 코드: 11 = ECONNREFUSED)
- 포트 5432 연결 타임아웃
- PostgreSQL 서비스가 포트에서 응답하지 않음

## 🚨 가능한 원인들

### 1. **RDS 인스턴스 상태 문제**
- 인스턴스가 아직 시작 중 (Creating → Available)
- 인스턴스가 중지된 상태 (Stopped)
- 인스턴스가 재시작 중 (Rebooting)

### 2. **VPC/Subnet 설정 문제**
- RDS가 Private Subnet에 있음
- Route Table에서 인터넷 게이트웨이로의 라우팅 없음
- Network ACL에서 차단

### 3. **RDS 설정 문제**
- 퍼블릭 액세스가 실제로는 No로 설정됨
- 잘못된 보안 그룹 연결
- RDS 인스턴스가 다른 VPC에 있음

### 4. **AWS 리전 문제**
- RDS가 다른 리전에 생성됨
- 현재 리전이 us-west-1이 아닐 수 있음

## 🔧 AWS 콘솔에서 확인할 사항

### 1. **RDS 인스턴스 상세 정보**
```
RDS → Databases → verifit-db

확인 사항:
- Status: Available (녹색)
- Engine: postgres
- DB instance class: db.t3.micro (프리티어)
- Publicly accessible: Yes
- VPC: vpc-xxxxx (default VPC)
- Subnet group: default
- Security groups: default (sg-xxxxx)
```

### 2. **보안 그룹 상세 확인**
```
EC2 → Security Groups → default (sg-xxxxx)

Inbound rules:
- Type: All traffic
- Protocol: All
- Port range: All
- Source: 0.0.0.0/0
```

### 3. **VPC 설정 확인**
```
VPC → Your VPCs → default VPC

확인 사항:
- State: Available
- CIDR: 172.31.0.0/16 (일반적)
```

### 4. **Route Table 확인**
```
VPC → Route Tables → default

확인 사항:
- Destination: 0.0.0.0/0
- Target: igw-xxxxx (Internet Gateway)
```

## 🧪 추가 테스트 방법

### 1. **다른 포트 테스트**
```bash
# SSH 포트 테스트 (22번 포트)
nc -zv verifit-db.cpk0oamsu0g6.us-west-1.rds.amazonaws.com 22

# HTTP 포트 테스트 (80번 포트)
nc -zv verifit-db.cpk0oamsu0g6.us-west-1.rds.amazonaws.com 80
```

### 2. **RDS 인스턴스 재시작**
```
RDS → Databases → verifit-db → Actions → Reboot
```

### 3. **새 RDS 인스턴스 생성**
만약 계속 문제가 있다면:
- 기존 인스턴스 삭제
- 새로 생성 (동일한 설정으로)

## 💡 임시 해결책

RDS 연결이 해결될 때까지 로컬 개발 계속:

```python
# app/core/config.py
database_url: str = "sqlite:///./verifit.db"
```

## 📋 체크리스트

- [ ] RDS 인스턴스 상태: Available
- [ ] 퍼블릭 액세스: Yes
- [ ] 보안 그룹: default (모든 포트 열림)
- [ ] VPC: default VPC
- [ ] Subnet: public subnet
- [ ] Route Table: 인터넷 게이트웨이 연결
- [ ] 리전: us-west-1

