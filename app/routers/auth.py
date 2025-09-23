from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.schemas.user import UserCreate, UserResponse, UserLogin, ApplicantSignupRequest, CompanySignupRequest
from app.services.auth_service import AuthService
from app.models.company import Company
from app.core.security import create_access_token
from app.models.user import User
from app.models.job_seeker import JobSeeker
from app.models.company import Company as CompanyModel
from app.core.security import get_password_hash

router = APIRouter()

@router.post("/login", response_model=dict)
async def login(
    user_data: UserLogin,
    db: Session = Depends(get_db)
):
    """로그인 API"""
    auth_service = AuthService(db)
    user = auth_service.authenticate_user(user_data.email, user_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.email})
    company_name = None
    user_name = None
    if user.user_type == "company":
        company = db.query(Company).filter(Company.user_id == user.id).first()
        if company:
            company_name = company.company_name
    else:
        # 구직자일 경우 이름 반환 (가능한 필드 우선순위: full_name -> email 로컬파트)
        try:
            from app.models.job_seeker import JobSeeker
            job_seeker = db.query(JobSeeker).filter(JobSeeker.user_id == user.id).first()
            if job_seeker and job_seeker.full_name:
                user_name = job_seeker.full_name
        except Exception:
            user_name = None
        if not user_name:
            # fullname이 없으면 이메일의 @ 앞부분을 대체로 사용
            user_name = (user.email.split("@", 1)[0]) if user.email else None
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user),
        "company_name": company_name,
        "user_name": user_name
    }

@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """회원가입 API"""
    auth_service = AuthService(db)
    
    # 이메일 중복 확인
    if auth_service.get_user_by_email(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 등록된 이메일입니다"
        )
    
    user = auth_service.create_user(user_data)
    return UserResponse.model_validate(user)


@router.post("/signup/applicant", response_model=UserResponse)
async def signup_applicant(
    payload: ApplicantSignupRequest,
    db: Session = Depends(get_db)
):
    """구직자 회원가입: users + job_seekers 동시 생성"""
    auth_service = AuthService(db)
    # 이메일 중복 검사
    if auth_service.get_user_by_email(payload.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="이미 등록된 이메일입니다")

    # 트랜잭션 처리
    try:
        hashed = get_password_hash(payload.password)
        user = User(email=payload.email, password=hashed, user_type="job_seeker")
        db.add(user)
        db.flush()

        job_seeker = JobSeeker(user_id=user.id, full_name=payload.name, email=payload.email)
        db.add(job_seeker)
        db.commit()
        db.refresh(user)
        return UserResponse.model_validate(user)
    except Exception:
        db.rollback()
        raise


@router.post("/signup/company", response_model=UserResponse)
async def signup_company(
    payload: CompanySignupRequest,
    db: Session = Depends(get_db)
):
    """기업 회원가입: users + companies 동시 생성"""
    auth_service = AuthService(db)
    if auth_service.get_user_by_email(payload.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="이미 등록된 이메일입니다")

    try:
        hashed = get_password_hash(payload.password)
        user = User(email=payload.email, password=hashed, user_type="company")
        db.add(user)
        db.flush()

        company = CompanyModel(
            user_id=user.id,
            company_name=payload.companyName,
            business_registration_number=payload.businessNumber
        )
        db.add(company)
        db.commit()
        db.refresh(user)
        return UserResponse.model_validate(user)
    except Exception:
        db.rollback()
        raise
