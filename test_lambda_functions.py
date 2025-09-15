#!/usr/bin/env python3
"""
Lambda 함수 테스트 스크립트
"""
import json
import boto3
import base64
from pathlib import Path

def test_bedrock_extractor():
    """Bedrock 개인정보 추출 Lambda 함수 테스트"""
    print("🧪 Bedrock 개인정보 추출 Lambda 함수 테스트")
    
    # 테스트 데이터
    test_text = """
    이름: 김철수
    전화번호: 010-1234-5678
    이메일: kim@example.com
    주소: 서울시 강남구 테헤란로 123
    생년월일: 1990-05-15
    성별: 남성
    """
    
    # Lambda 함수 호출
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    payload = {
        'extracted_text': test_text
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName='verifit-bedrock-extractor',
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read())
        print("✅ Bedrock 추출 결과:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"❌ Bedrock 추출 테스트 실패: {str(e)}")

def test_ocr_extractor():
    """OCR 개인정보 추출 Lambda 함수 테스트"""
    print("\n🧪 OCR 개인정보 추출 Lambda 함수 테스트")
    
    # OCR로 추출된 텍스트 시뮬레이션
    ocr_text = """
    주민등록증
    성명: 이영희
    주민등록번호: 901215-2345678
    주소: 경기도 성남시 분당구 판교역로 456
    발급일: 2020.01.15
    """
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    payload = {
        'extracted_text': ocr_text,
        'document_type': 'id_card'
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName='verifit-ocr-extractor',
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read())
        print("✅ OCR 추출 결과:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"❌ OCR 추출 테스트 실패: {str(e)}")

def test_text_extractor():
    """텍스트 개인정보 추출 Lambda 함수 테스트"""
    print("\n🧪 텍스트 개인정보 추출 Lambda 함수 테스트")
    
    # OCR로 추출된 텍스트 시뮬레이션 (실제로는 ocr_service.py에서 추출됨)
    extracted_text = """
    주민등록증
    성명: 이영희
    주민등록번호: 901215-2345678
    주소: 경기도 성남시 분당구 판교역로 456
    발급일: 2020.01.15
    """
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    payload = {
        'extracted_text': extracted_text,
        'document_type': 'id_card'
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName='verifit-text-extractor',
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read())
        print("✅ 텍스트 개인정보 추출 결과:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"❌ 텍스트 개인정보 추출 테스트 실패: {str(e)}")

def test_with_api_gateway_format():
    """API Gateway 형식으로 Lambda 함수 테스트"""
    print("\n🧪 API Gateway 형식 테스트")
    
    test_text = """
    운전면허증
    성명: 박민수
    면허번호: 11-12-345678-90
    생년월일: 1985.03.20
    주소: 부산시 해운대구 센텀중앙로 789
    """
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # API Gateway 형식의 이벤트
    api_gateway_event = {
        'body': json.dumps({
            'extracted_text': test_text,
            'document_type': 'driver_license'
        })
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName='verifit-ocr-extractor',
            InvocationType='RequestResponse',
            Payload=json.dumps(api_gateway_event)
        )
        
        result = json.loads(response['Payload'].read())
        print("✅ API Gateway 형식 테스트 결과:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"❌ API Gateway 형식 테스트 실패: {str(e)}")

def create_test_image():
    """테스트용 샘플 이미지 생성 안내"""
    print("""
📸 OCR 서비스 사용 안내:

OCR은 기존 ocr_service.py에서 처리됩니다.
Lambda 함수는 OCR로 추출된 텍스트만 받아서 개인정보를 추출합니다.

워크플로우:
1. 이미지 업로드 → ocr_service.py (Mathpix) → 텍스트 추출
2. 추출된 텍스트 → Lambda 함수 → 개인정보 추출
3. 결과 반환

🔑 Mathpix API 키 설정:
- ocr_service.py에서 사용하는 Mathpix API 키 설정 필요
- Mathpix 계정: https://mathpix.com/
- 설정 파일: app/core/config.py
""")

if __name__ == "__main__":
    print("🔧 VeriFit Lambda 함수 테스트 시작")
    print("=" * 50)
    
    # 1. Bedrock 개인정보 추출 테스트
    test_bedrock_extractor()
    
    # 2. OCR 개인정보 추출 테스트
    test_ocr_extractor()
    
    # 3. API Gateway 형식 테스트
    test_with_api_gateway_format()
    
    # 4. 텍스트 개인정보 추출 테스트
    test_text_extractor()
    
    # 5. 테스트 이미지 생성 안내
    create_test_image()
    
    print("\n" + "=" * 50)
    print("✅ 모든 테스트 완료!")
    print("\n📋 테스트 결과 확인:")
    print("- Bedrock 개인정보 추출: 텍스트에서 개인정보 추출")
    print("- OCR 개인정보 추출: OCR 텍스트에서 개인정보 추출")
    print("- API Gateway 형식: HTTP 요청 형식 테스트")
    print("- 텍스트 개인정보 추출: OCR로 추출된 텍스트에서 개인정보 추출")
