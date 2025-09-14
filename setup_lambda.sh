#!/bin/bash

echo "🔧 VeriFit Lambda 설정 시작"

# 1. 필요한 디렉토리 생성
echo "📁 디렉토리 생성 중..."
mkdir -p lambda_package

# 2. 배포 패키지 생성
echo "📦 배포 패키지 생성 중..."
python3 -m pip install -r lambda_requirements.txt -t lambda_package/
cp lambda_bedrock_handler.py lambda_package/

# 3. ZIP 파일 생성
echo "🗜️ ZIP 파일 생성 중..."
cd lambda_package
zip -r ../lambda_bedrock.zip .
cd ..

echo "✅ 배포 패키지 생성 완료: lambda_bedrock.zip"

# 4. AWS CLI 설정 확인
echo "🔍 AWS CLI 설정 확인 중..."
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ AWS CLI가 설정되지 않았습니다."
    echo "다음 명령어로 AWS CLI를 설정하세요:"
    echo "aws configure"
    exit 1
fi

echo "✅ AWS CLI 설정 확인 완료"

# 5. Lambda 함수 배포
echo "🚀 Lambda 함수 배포 중..."
FUNCTION_NAME="verifit-bedrock-extractor"
REGION="us-west-1"

# 함수가 이미 존재하는지 확인
if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION > /dev/null 2>&1; then
    echo "📝 기존 함수 업데이트 중..."
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://lambda_bedrock.zip \
        --region $REGION
else
    echo "🆕 새 함수 생성 중..."
    # 관리자가 제공한 IAM Role 사용
    ROLE_ARN="arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/SafeRoleForUser-seoul-ht-01"
    
    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --runtime python3.9 \
        --role $ROLE_ARN \
        --handler lambda_bedrock_handler.lambda_handler \
        --zip-file fileb://lambda_bedrock.zip \
        --description "VeriFit 개인정보 추출용 Bedrock Lambda 함수" \
        --timeout 60 \
        --memory-size 512 \
        --region $REGION
fi

# 6. 환경 변수 설정
echo "⚙️ 환경 변수 설정 중..."
aws lambda update-function-configuration \
    --function-name $FUNCTION_NAME \
    --environment Variables='{
        "AWS_REGION":"us-east-1",
        "BEDROCK_MODEL_ID":"anthropic.claude-3-5-sonnet-20240620-v1:0"
    }' \
    --region $REGION

echo "✅ Lambda 함수 설정 완료"

# 7. 테스트 실행
echo "🧪 Lambda 함수 테스트 중..."
aws lambda invoke \
    --function-name $FUNCTION_NAME \
    --payload '{"extracted_text":"테스트 텍스트입니다.","model_id":"anthropic.claude-3-5-sonnet-20240620-v1:0"}' \
    --region $REGION \
    test_output.json

echo "📊 테스트 결과:"
cat test_output.json | jq '.'

# 8. 정리
echo "🧹 임시 파일 정리 중..."
rm -rf lambda_package
rm -f test_output.json

echo "🎉 Lambda 설정 완료!"
echo ""
echo "📋 다음 단계:"
echo "1. PM2 서버 재시작: pm2 restart verifit-backend"
echo "2. 개인정보 추출 API 테스트"
echo ""
echo "🔧 Lambda 함수 정보:"
echo "- 함수명: $FUNCTION_NAME"
echo "- 리전: $REGION"
echo "- 핸들러: lambda_bedrock_handler.lambda_handler"
