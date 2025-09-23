#!/bin/bash

# Lambda 함수 배포 스크립트 - KB 인덱싱 함수

FUNCTION_NAME="verifit-kb-ingest"
ZIP_FILE="lambda_kb_ingest.zip"

echo "🚀 Lambda KB 인덱싱 함수 배포 시작..."

# 1. 기존 zip 파일 삭제
if [ -f "$ZIP_FILE" ]; then
    rm "$ZIP_FILE"
    echo "✅ 기존 zip 파일 삭제 완료"
fi

# 2. 필요한 파일들을 zip으로 압축
zip -r "$ZIP_FILE" \
    lambda_kb_ingest.py \
    requirements_lambda.txt

echo "✅ Lambda 함수 파일 압축 완료"

# 3. Lambda 함수 업데이트 (함수가 이미 존재하는 경우)
if aws lambda get-function --function-name "$FUNCTION_NAME" >/dev/null 2>&1; then
    echo "📦 기존 Lambda 함수 업데이트 중..."
    aws lambda update-function-code \
        --function-name "$FUNCTION_NAME" \
        --zip-file "fileb://$ZIP_FILE"
    echo "✅ Lambda 함수 업데이트 완료"
else
    echo "❌ Lambda 함수가 존재하지 않습니다. 먼저 AWS 콘솔에서 함수를 생성해주세요."
    echo "함수명: $FUNCTION_NAME"
    echo "핸들러: lambda_kb_ingest.lambda_handler"
    echo "런타임: python3.11"
    echo "타임아웃: 120초"
    echo "메모리: 512MB"
fi

echo "🎉 KB 인덱싱 함수 배포 완료!"


