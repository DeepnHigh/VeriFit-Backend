-- document_type_enum에 'github' 값 추가
ALTER TYPE document_type_enum ADD VALUE 'github';

-- job_seekers 테이블에 full_text 컬럼 추가
ALTER TABLE public.job_seekers
ADD COLUMN IF NOT EXISTS full_text text;

-- job_seekers 테이블에 behavior_text 컬럼 추가
ALTER TABLE public.job_seekers
ADD COLUMN IF NOT EXISTS behavior_text text;
