#!/usr/bin/env python3
"""
AWS Lambda 함수 배포 스크립트
"""
import boto3
import zipfile
import os
import subprocess
import sys

def create_deployment_package():
    """Lambda 배포 패키지 생성"""
    print("📦 Lambda 배포 패키지 생성 중...")
    
    # requirements.txt에서 패키지 설치
    subprocess.run([
        sys.executable, "-m", "pip", "install", 
        "-r", "lambda_requirements.txt", 
        "-t", "lambda_package"
    ], check=True)
    
    # Lambda 핸들러 파일 복사
    os.system("cp lambda_bedrock_handler.py lambda_package/")
    
    # ZIP 파일 생성
    with zipfile.ZipFile("lambda_bedrock.zip", "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk("lambda_package"):
            for file in files:
                file_path = os.path.join(root, file)
                arc_path = os.path.relpath(file_path, "lambda_package")
                zipf.write(file_path, arc_path)
    
    print("✅ 배포 패키지 생성 완료: lambda_bedrock.zip")

def deploy_lambda():
    """Lambda 함수 배포"""
    print("🚀 Lambda 함수 배포 중...")
    
    # AWS Lambda 클라이언트 초기화
    lambda_client = boto3.client('lambda', region_name='us-west-1')
    
    function_name = "verifit-bedrock-extractor"
    
    try:
        # 함수가 이미 존재하는지 확인
        lambda_client.get_function(FunctionName=function_name)
        print(f"📝 기존 함수 업데이트: {function_name}")
        
        # 함수 코드 업데이트
        with open("lambda_bedrock.zip", "rb") as zip_file:
            lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=zip_file.read()
            )
        
        print("✅ Lambda 함수 업데이트 완료")
        
    except lambda_client.exceptions.ResourceNotFoundException:
        print(f"🆕 새 함수 생성: {function_name}")
        
        # 새 함수 생성
        with open("lambda_bedrock.zip", "rb") as zip_file:
            lambda_client.create_function(
                FunctionName=function_name,
                Runtime='python3.9',
                Role='arn:aws:iam::YOUR_ACCOUNT_ID:role/SafeRoleForUser-seoul-ht-01',  # 관리자가 제공한 Role
                Handler='lambda_bedrock_handler.lambda_handler',
                Code={'ZipFile': zip_file.read()},
                Description='VeriFit 개인정보 추출용 Bedrock Lambda 함수',
                Timeout=60,
                MemorySize=512
            )
        
        print("✅ Lambda 함수 생성 완료")
    
    # 환경 변수 설정
    lambda_client.update_function_configuration(
        FunctionName=function_name,
        Environment={
            'Variables': {
                'AWS_REGION': 'us-east-1',
                'BEDROCK_MODEL_ID': 'anthropic.claude-3-5-sonnet-20240620-v1:0'
            }
        }
    )
    
    print("✅ 환경 변수 설정 완료")

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
""")

if __name__ == "__main__":
    print("🔧 VeriFit Lambda 배포 시작")
    
    # 1. 배포 패키지 생성
    create_deployment_package()
    
    # 2. IAM Role 안내
    create_iam_role()
    
    # 3. Lambda 배포 (IAM Role 설정 후 실행)
    # deploy_lambda()
    
    print("""
📋 다음 단계:
1. IAM Role을 생성하고 ARN을 deploy_lambda.py에 입력
2. python deploy_lambda.py 실행
3. Lambda 함수 URL 생성 (선택사항)
4. VeriFit 백엔드에서 Lambda 함수 호출하도록 수정
""")
