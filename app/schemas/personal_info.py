from pydantic import BaseModel
from typing import Optional

class PersonalInfo(BaseModel):
    """개인정보 추출 결과"""
    email: Optional[str] = None
    phone: Optional[str] = None
    education_level: Optional[str] = None
    university: Optional[str] = None
    major: Optional[str] = None
    graduation_year: Optional[str] = None
    total_experience_years: Optional[int] = None
    company_name: Optional[str] = None

class PersonalInfoResponse(BaseModel):
    """개인정보 파싱 API 응답"""
    success: bool
    personal_info: PersonalInfo
    extracted_text_length: int
    processed_files: list[str]
    message: str
