#!/usr/bin/env python3
"""
Lambda 질문 생성 함수 테스트 스크립트
"""

import asyncio
import json
from app.services.lambda_bedrock_service import LambdaBedrockService

async def test_question_generation():
    """질문 생성 Lambda 함수 테스트"""
    
    # 테스트용 채용공고 데이터
    test_job_posting = {
        "title": "백엔드 개발자",
        "position_level": "시니어",
        "employment_type": "정규직",
        "location": "서울",
        "salary_min": 5000,
        "salary_max": 7000,
        "main_tasks": "FastAPI 기반 백엔드 API 개발, 데이터베이스 설계 및 최적화, AWS 클라우드 인프라 관리",
        "requirements": [
            "Python 3년 이상 경험",
            "FastAPI 또는 Django 경험",
            "PostgreSQL 경험",
            "AWS 서비스 경험"
        ],
        "preferred": "Docker, Kubernetes 경험, 팀 리딩 경험",
        "hard_skills": ["Python", "FastAPI", "PostgreSQL", "AWS"],
        "soft_skills": ["커뮤니케이션", "문제해결", "팀워크"],
        "culture": "고객 중심으로 문제를 정의하고 데이터 기반으로 의사결정합니다.\n빠른 실행과 학습을 중시하며 작은 실험을 반복합니다.\n직군/직급에 상관없는 수평적 커뮤니케이션을 지향합니다.\n동료를 신뢰하고 자율과 책임을 균형 있게 갖습니다.\n투명한 정보 공유와 원활한 피드백 문화를 지향합니다.",
        "benefits": "유연근무제(코어타임 11-16시)\n원격/하이브리드 근무 선택\n자기계발비 연 120만원\n최신 장비 및 주변기기 제공\n점심/야근 식대 지원\n프리미엄 사내 스낵바\n건강검진 및 단체 상해보험\n리프레시 휴가(연 5일 추가)\n도서/세미나/컨퍼런스 지원\n출산/육아 특별 휴가 및 보조금"
    }
    
    print("🚀 Lambda 질문 생성 함수 테스트 시작...")
    print(f"📋 테스트 채용공고: {test_job_posting['title']}")
    print("-" * 50)
    
    try:
        # LambdaBedrockService 인스턴스 생성
        bedrock_service = LambdaBedrockService()
        
        # 질문 생성 요청
        print("📤 Lambda 함수 호출 중...")
        response = await bedrock_service.generate_interview_questions(test_job_posting)
        
        print("✅ Lambda 함수 응답 수신!")
        print(f"📊 응답 상태: {response.get('success', False)}")
        
        if response.get('success', False):
            questions = response.get('questions', [])
            print(f"📝 생성된 질문 수: {len(questions)}")
            print("\n🎯 생성된 면접 질문들:")
            print("-" * 30)
            
            for i, question in enumerate(questions, 1):
                print(f"{i}. {question}")
            
            print("-" * 30)
            print("🎉 테스트 성공!")
            
        else:
            print("❌ 테스트 실패!")
            print(f"오류: {response.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_question_generation())
