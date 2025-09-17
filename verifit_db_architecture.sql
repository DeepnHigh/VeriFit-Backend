// AI 기반 채용 플랫폼 데이터베이스 스키마
// 적성검사와 행동 시뮬레이션을 제외한 핵심 기능들

// ==============================================
// 사용자 관리
// ==============================================

Table users {
  id uuid [primary key, default: `uuid_generate_v4()`]
  password varchar(255) // OAuth 사용자는 NULL 가능
  provider enum('local', 'google', 'github', 'linkedin', 'kakao', 'naver') [default: 'local']
  provider_id varchar(255) // OAuth 제공자의 사용자 ID
  user_type enum('company', 'job_seeker') [not null]
  is_active boolean [default: true]
  last_login_at timestamp // 마지막 로그인 시간
  created_at timestamp [default: `now()`]
  
  indexes {
    provider
    provider_id
    user_type
    is_active
  }
}

Table job_seekers {
  id uuid [primary key, default: `uuid_generate_v4()`]
  user_id uuid [ref: > users.id, not null]
  full_name varchar(100) [not null]
  phone varchar(20)
  email varchar(255)
  profile_picture varchar(500)
  bio text // 자기소개/프로필 소개
  total_experience_years integer // 총 경력 년수
  company_name varchar(200) // 최근 직장
  education_level enum('high_school', 'associate', 'bachelor', 'master', 'phd')
  university varchar(200) // 대학교명
  major varchar(100) // 전공
  graduation_year integer // 졸업년도
  github_repositories jsonb // GitHub 레포지토리 URL 리스트
  portfolios jsonb // 포트폴리오
  resumes jsonb // 이력서
  awards jsonb // 수상경력 리스트
  certificates jsonb // 증명서 리스트
  qualifications jsonb // 자격증 리스트
  papers jsonb // 논문 리스트
  cover_letters jsonb // 자기소개서 리스트
  other_documents jsonb // 기타 자료 리스트
  location varchar(200) // 거주지/위치
  profile_completion_percentage decimal(5,2) [default: 0.00] // 프로필 완성도
  last_profile_update timestamp // 마지막 프로필 업데이트
  is_profile_public boolean [default: true] // 프로필 공개 여부
  
  indexes {
    user_id
    total_experience_years
    education_level
    location
    is_profile_public
  }
}

Table job_seeker_documents {
  id uuid [primary key, default: `uuid_generate_v4()`]
  job_seeker_id uuid [ref: > job_seekers.id, not null]
  document_type enum('portfolio', 'resume', 'award', 'certificate', 'qualification', 'paper', 'cover_letter', 'other') [not null]
  file_name varchar(255) [not null]
  file_url varchar(500) [not null]
  file_size integer // bytes
  mime_type varchar(100) // 타입 (application/pdf)
  uploaded_at timestamp [default: `now()`]
  
  indexes {
    job_seeker_id
    document_type
    uploaded_at
  }
}

// AI 에이전트 관리 테이블
Table job_seeker_ai_agents {
  id uuid [primary key, default: `uuid_generate_v4()`]
  job_seeker_id uuid [ref: > job_seekers.id, not null]
  ai_agent_completion_percentage decimal(5,2) [default: 0.00] // AI 에이전트 완성도
  
  indexes {
    job_seeker_id
  }
}

// Big5 성격검사 결과 테이블
Table big5_test_results {
  id uuid [primary key, default: `uuid_generate_v4()`]
  job_seeker_id uuid [ref: > job_seekers.id, not null]
  test_date timestamp [default: `now()`]
  
  // Big5 주요 차원 점수 (0-100 스케일)
  openness_score decimal(5,2) [not null] // 개방성 점수
  conscientiousness_score decimal(5,2) [not null] // 성실성 점수
  extraversion_score decimal(5,2) [not null] // 외향성 점수
  agreeableness_score decimal(5,2) [not null] // 우호성 점수
  neuroticism_score decimal(5,2) [not null] // 신경성 점수
  
  // Big5 결과 레벨 (high, neutral, low)
  openness_level varchar(10) [not null] // 개방성 레벨
  conscientiousness_level varchar(10) [not null] // 성실성 레벨
  extraversion_level varchar(10) [not null] // 외향성 레벨
  agreeableness_level varchar(10) [not null] // 우호성 레벨
  neuroticism_level varchar(10) [not null] // 신경성 레벨
  
  // 세부 특성 점수 (각 차원당 6개)
  openness_facets jsonb // 개방성 세부 특성 (상상력, 예술성, 감정성, 모험성, 지성, 자유주의)
  conscientiousness_facets jsonb // 성실성 세부 특성 (자기효능감, 체계성, 의무감, 성취추구, 자기통제, 신중함)
  extraversion_facets jsonb // 외향성 세부 특성 (친화성, 사교성, 주장성, 활동성, 자극추구, 쾌활함)
  agreeableness_facets jsonb // 우호성 세부 특성 (신뢰, 도덕성, 이타성, 협력, 겸손, 공감)
  neuroticism_facets jsonb // 신경성 세부 특성 (불안, 분노, 우울, 자의식, 무절제, 취약성)
  
  // 전문적인 해석 결과
  interpretations jsonb // 전문적인 해석 텍스트 (한국어/영어)
  raw_scores jsonb // 원본 점수 데이터
  
  indexes {
    job_seeker_id
    test_date
    openness_score
    conscientiousness_score
    extraversion_score
    agreeableness_score
    neuroticism_score
  }
}

// 행동검사 결과 테이블도 추가해야함

// AI 학습용 질문 템플릿 테이블
Table ai_learning_questions {
  id uuid [primary key, default: `uuid_generate_v4()`]
  question_text text [not null] // 질문 내용
  display_order integer [default: 0] // 표시 순서
  
  indexes {
    display_order
  }
}

// 구직자별 AI 학습 질문 답변 테이블
Table job_seeker_ai_learning_responses {
  id uuid [primary key, default: `uuid_generate_v4()`]
  job_seeker_id uuid [ref: > job_seekers.id, not null]
  question_id uuid [ref: > ai_learning_questions.id, not null]
  answer_text text [not null] // 답변 내용
  response_date timestamp [default: `now()`]
  
  indexes {
    job_seeker_id
    question_id
    response_date
  }
}

// Table job_seeker_work_experience {
//   id uuid [primary key, default: `uuid_generate_v4()`]
//   job_seeker_id uuid [ref: > job_seekers.id, not null]
//   company_name varchar(200) [not null]
//   position varchar(100) [not null]
//   start_date date [not null]
//   end_date date
//   is_current boolean [default: false]
//   description text
//   achievements text
//   created_at timestamp [default: `now()`]
  
//   indexes {
//     job_seeker_id
//     start_date
//     is_current
//   }
// }

// ==============================================
// 기업 관련
// ==============================================

Table companies {
  id uuid [primary key, default: `uuid_generate_v4()`]
  user_id uuid [ref: > users.id, not null]
  company_name varchar(200) [not null]
  industry varchar(100)
  company_size enum('startup', 'small', 'medium', 'large', 'enterprise')
  website varchar(255)
  description text
  logo_url varchar(500)
  founded_year integer // 설립년도
  employee_count integer // 직원 수
  headquarters_location varchar(200) // 본사 위치
  business_registration_number varchar(50) // 사업자등록번호
  company_status enum('active', 'inactive', 'suspended') [default: 'active']
  
  indexes {
    user_id
    company_name
    industry
    company_status
  }
}

Table job_postings {
  id uuid [primary key, default: `uuid_generate_v4()`]
  company_id uuid [ref: > companies.id, not null]
  title varchar(200) [not null]
  position_level enum('intern', 'junior', 'mid', 'senior', 'lead', 'manager')
  employment_type enum('full_time', 'part_time', 'contract', 'internship')
  location varchar(200)
  salary_min integer
  salary_max integer
  main_tasks text [not null]
  requirements text
  preferred text
  application_deadline date
  hard_skills jsonb
  soft_skills jsonb
  is_active boolean [default: true]
  created_at timestamp [default: `now()`]
  updated_at timestamp [default: `now()`]
  
  indexes {
    company_id
    title
    position_level
    employment_type
    is_active
    application_deadline
  }
}

Table evaluation_criteria {
  id uuid [primary key, default: `uuid_generate_v4()`]
  job_posting_id uuid [ref: > job_postings.id, not null]
  skill_type enum('hard_skill', 'soft_skill') [not null]
  skill_name varchar(100) [not null]
  skill_description text
  percentage decimal(5,2) [default: 0.00] // 비중 (0.00 ~ 100.00)
  
  indexes {
    job_posting_id
    skill_type
  }
}

// ==============================================
// 지원 및 평가
// ==============================================

Table applications {
  id uuid [primary key, default: `uuid_generate_v4()`]
  job_posting_id uuid [ref: > job_postings.id, not null]
  job_seeker_id uuid [ref: > job_seekers.id, not null]
  application_status enum('submitted', 'under_review', 'ai_evaluated', 'shortlisted', 'rejected', 'hired') [default: 'submitted']
  applied_at timestamp [default: `now()`]
  evaluated_at timestamp
  notes text
  
  indexes {
    job_posting_id
    job_seeker_id
    application_status
    applied_at
  }
}

Table ai_evaluations {
  id uuid [primary key, default: `uuid_generate_v4()`]
  application_id uuid [ref: > applications.id, not null]
  // 순위 페이지
  hard_score decimal(5,2) [not null] // 0.00 ~ 100.00
  soft_score decimal(5,2) [not null] // 0.00 ~ 100.00
  total_score decimal(5,2) [not null] // 0.00 ~ 100.00
  ai_summary text [not null] // 총평
  // 상세보기 페이지
  hard_detail_scores jsonb // 하드 스킬 상세 분석 점수
  soft_detail_scores jsonb // 소프트 스킬 상세 분석 점수
  strengths_content text // 강점 - 내용
  strengths_opinion text // 강점 - AI면접관 의견
  strengths_evidence text // 강점 - 근거
  concerns_content text // 우려사항 - 내용
  concerns_opinion text // 우려사항 - AI면접관 의견
  concerns_evidence text // 우려사항 - 근거
  followup_content text // 후속검증 제안 - 내용
  followup_opinion text // 후속검증 제안 - AI면접관 의견
  followup_evidence text // 후속검증 제안 - 근거
  final_opinion text // AI 면접관 최종 의견
  created_at timestamp [default: `now()`]
  
  indexes {
    application_id
  }
}

// AI 면접(agent V/S agent) 질문-답변 채팅 (지원자별)
Table ai_interview_messages {
  id uuid [primary key, default: `uuid_generate_v4()`]
  application_id uuid [ref: > applications.id, not null]
  sender enum('company_ai', 'jobseeker_ai') [not null] // 발화자
  message_type enum('question', 'answer', 'system', 'other') [default: 'other']
  content text [not null] // 메시지 본문
  turn_number integer [not null] // 대화 턴 번호 (1=질문, 2=답변, 3=질문...)
  highlight_turns jsonb // 하이라이트 턴 리스트 (예: [3,4,7,8])
  created_at timestamp [default: `now()`]
  
  indexes {
    application_id
    (application_id, turn_number)
    turn_number
    highlight_turns
    sender
    created_at
  }
}

Table ai_overall_report {
  id uuid [primary key, default: `uuid_generate_v4()`]
  job_posting_id uuid [ref: > job_postings.id, not null]
  // 채용 현황 통계 (계산 불가능한 값들만 저장)
  total_applications integer [not null] // 총 지원자 수
  ai_evaluated_count integer [not null] // AI 평가 완료 수  
  ai_recommended_count integer [not null] // AI면접관 추천 수
  // AI 분석 결과
  hard_skill_evaluation jsonb [not null] // 하드스킬 평가 항목 및 내용
  soft_skill_evaluation jsonb [not null] // 소프트스킬 평가 항목 및 내용
  overall_review text [not null] // AI면접관 총평
  created_at timestamp [default: `now()`]
  
  indexes {
    job_posting_id
    created_at
  }
}
