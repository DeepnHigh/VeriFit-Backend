from sqlalchemy import Column, String, Text, Integer, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.database.database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    company_name = Column(String(200), nullable=False)
    industry = Column(String(100))
    company_size = Column(Enum('startup', 'small', 'medium', 'large', 'enterprise', name='company_size_enum'))
    website = Column(String(255))
    description = Column(Text)
    logo_url = Column(String(500))
    founded_year = Column(Integer)
    employee_count = Column(Integer)
    headquarters_location = Column(String(200))
    business_registration_number = Column(String(50))
    company_status = Column(Enum('active', 'inactive', 'suspended', name='company_status_enum'), default='active')

    # 관계 설정
    user = relationship("User", back_populates="company")
    job_postings = relationship("JobPosting", back_populates="company")


