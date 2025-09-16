#!/usr/bin/env python3
"""
AWS Lambda 함수 배포 스크립트
"""
import boto3
import zipfile
import os
import subprocess
import sys

def create_deployment_package(lambda_file: str, zip_name: str):
    """Lambda 배포 패키지 생성"""
    print(f"📦 Lambda 배포 패키지 생성 중... ({lambda_file})")
    
    # 패키지 디렉토리 정리
    if os.path.exists("lambda_package"):
        os.system("rm -rf lambda_package")
    os.makedirs("lambda_package", exist_ok=True)
    
    # requirements.txt에서 패키지 설치
    subprocess.run([
        sys.executable, "-m", "pip", "install", 
        "-r", "lambda_requirements.txt", 
        "-t", "lambda_package"
    ], check=True)
    
    # Lambda 핸들러 파일 복사
    os.system(f"cp {lambda_file} lambda_package/")
    
    # ZIP 파일 생성
    with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk("lambda_package"):
            for file in files:
                file_path = os.path.join(root, file)
                arc_path = os.path.relpath(file_path, "lambda_package")
                zipf.write(file_path, arc_path)
    
    print(f"✅ 배포 패키지 생성 완료: {zip_name}")

def deploy_lambda(function_name: str, zip_file: str, handler: str, description: str):
    """Lambda 함수 배포"""
    print(f"🚀 Lambda 함수 배포 중... ({function_name})")
    
    # AWS Lambda 클라이언트 초기화 (us-east-1로 변경)
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    try:
        # 함수가 이미 존재하는지 확인
        lambda_client.get_function(FunctionName=function_name)
        print(f"📝 기존 함수 업데이트: {function_name}")
        
        # 함수 코드 업데이트
        with open(zip_file, "rb") as zip_file_obj:
            lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=zip_file_obj.read()
            )
        
        print("✅ Lambda 함수 코드 업데이트 완료")

        # 기존 함수도 타임아웃/메모리/환경변수 갱신
        lambda_client.update_function_configuration(
            FunctionName=function_name,
            Timeout=120,            # 최소 120초 권장
            MemorySize=1024,        # 1024MB 권장
            Environment={'Variables': {
                'AWS_REGION': 'us-east-1',
                'BEDROCK_MODEL_ID': 'anthropic.claude-3-5-sonnet-20240620-v1:0'
            }}
        )
        print("✅ Lambda 함수 구성(타임아웃/메모리/환경변수) 업데이트 완료")
        
    except lambda_client.exceptions.ResourceNotFoundException:
        print(f"🆕 새 함수 생성: {function_name}")
        
        # 새 함수 생성
        with open(zip_file, "rb") as zip_file_obj:
            lambda_client.create_function(
                FunctionName=function_name,
                Runtime='python3.9',
                Role='arn:aws:iam::YOUR_ACCOUNT_ID:role/SafeRoleForUser-seoul-ht-01',  # 관리자가 제공한 Role
                Handler=handler,
                Code={'ZipFile': zip_file_obj.read()},
                Description=description,
                Timeout=120,  # 초기 타임아웃 설정
                MemorySize=1024  # 메모리 증가
            )
        
        print("✅ Lambda 함수 생성 완료")
    
    print("ℹ️ 구성 업데이트 완료")

def create_iam_role():
    """Lambda용 IAM Role 생성 (수동으로 실행 필요)"""
    print("""
🔐 IAM Role 생성이 필요합니다. AWS 콘솔에서 다음 단계를 수행하세요:

1. IAM 콘솔로 이동
2. "역할" → "역할 만들기" 클릭
3. "AWS 서비스" → "Lambda" 선택
4. 다음 정책 연결:
   - AWSLambdaBasicExecutionRole
   - AmazonBedrockFullAccess (또는 필요한 최소 권한)
5. 역할 이름: SafeRoleForUser-seoul-ht-01
6. 역할 ARN을 deploy_lambda.py의 YOUR_ACCOUNT_ID 부분에 입력

또는 AWS CLI로:
aws iam create-role --role-name SafeRoleForUser-seoul-ht-01 --assume-role-policy-document '{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}'

aws iam attach-role-policy --role-name SafeRoleForUser-seoul-ht-01 --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam attach-role-policy --role-name SafeRoleForUser-seoul-ht-01 --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess

📝 Lambda 함수 사용법:
1. OCR은 기존 ocr_service.py에서 처리
2. Lambda 함수는 OCR로 추출된 텍스트만 받아서 개인정보 추출
3. 워크플로우: 이미지 → ocr_service.py → Lambda 함수 → 개인정보
""")

def deploy_all_lambdas():
    """모든 Lambda 함수 배포"""
    print("🔧 VeriFit Lambda 배포 시작")
    
    # Lambda 함수 정의
    lambda_functions = [
        {
            'file': 'lambda_bedrock_handler.py',
            'zip': 'lambda_bedrock.zip',
            'name': 'verifit-bedrock-extractor',
            'handler': 'lambda_bedrock_handler.lambda_handler',
            'description': 'VeriFit 개인정보 추출용 Bedrock Lambda 함수'
        },
        {
            'file': 'lambda_ocr_personal_info_extractor.py',
            'zip': 'lambda_ocr_extractor.zip',
            'name': 'verifit-ocr-extractor',
            'handler': 'lambda_ocr_personal_info_extractor.lambda_handler',
            'description': 'VeriFit OCR 텍스트 개인정보 추출 Lambda 함수'
        },
        {
            'file': 'lambda_text_personal_info_extractor.py',
            'zip': 'lambda_text_extractor.zip',
            'name': 'verifit-text-extractor',
            'handler': 'lambda_text_personal_info_extractor.lambda_handler',
            'description': 'VeriFit 텍스트 개인정보 추출 Lambda 함수 (OCR 텍스트 → 개인정보)'
        }
    ]
    
    # 각 Lambda 함수 배포
    for func in lambda_functions:
        print(f"\n📦 {func['name']} 배포 중...")
        
        # 1. 배포 패키지 생성
        create_deployment_package(func['file'], func['zip'])
        
        # 2. Lambda 함수 배포 (IAM Role 설정 후 실행)
        # deploy_lambda(
        #     func['name'], 
        #     func['zip'], 
        #     func['handler'], 
        #     func['description']
        # )
    
    print("\n✅ 모든 Lambda 함수 배포 패키지 생성 완료!")
    
    # 3. IAM Role 안내
    create_iam_role()

if __name__ == "__main__":
    deploy_all_lambdas()
    
    print("""
📋 다음 단계:
1. IAM Role을 생성하고 ARN을 deploy_lambda.py에 입력
2. deploy_lambda() 함수 호출 주석 해제 후 python deploy_lambda.py 실행
3. Lambda 함수 URL 생성 (선택사항)
4. VeriFit 백엔드에서 Lambda 함수 호출하도록 수정

🔗 Lambda 함수들:
- verifit-bedrock-extractor: 텍스트에서 개인정보 추출
- verifit-ocr-extractor: OCR 텍스트에서 개인정보 추출  
- verifit-text-extractor: OCR로 추출된 텍스트에서 개인정보 추출 (단순화된 버전)

📋 워크플로우:
1. 이미지 업로드 → ocr_service.py (Mathpix) → 텍스트 추출
2. 추출된 텍스트 → Lambda 함수 → 개인정보 추출
3. 결과 반환
""")
