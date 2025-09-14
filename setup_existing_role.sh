#!/bin/bash

echo "🔐 기존 IAM Role에 Bedrock 정책 추가"

ROLE_NAME="SafeRoleForUser-seoul-ht-01"
POLICY_NAME="lambda-bedrock-policy"

# 1. 기존 Role 확인
echo "🔍 기존 IAM Role 확인 중..."
if ! aws iam get-role --role-name $ROLE_NAME > /dev/null 2>&1; then
    echo "❌ IAM Role을 찾을 수 없습니다: $ROLE_NAME"
    echo "관리자에게 Role 생성 요청을 하세요."
    exit 1
fi

echo "✅ IAM Role 확인 완료: $ROLE_NAME"

# 2. Bedrock 정책 생성
echo "📝 Bedrock 정책 생성 중..."
cat > bedrock-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            "Resource": [
                "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0"
            ]
        }
    ]
}
EOF

# 3. Bedrock 정책 생성 및 연결
echo "🔗 Bedrock 정책 생성 및 연결 중..."
aws iam create-policy \
    --policy-name $POLICY_NAME \
    --policy-document file://bedrock-policy.json

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn arn:aws:iam::$ACCOUNT_ID:policy/$POLICY_NAME

# 4. Role ARN 출력
echo "✅ IAM Role 정책 추가 완료"
echo "📋 Role ARN: arn:aws:iam::$ACCOUNT_ID:role/$ROLE_NAME"

# 5. 정리
rm -f bedrock-policy.json

echo "🎉 IAM Role 설정 완료!"
echo ""
echo "📋 다음 단계:"
echo "1. ./setup_lambda.sh 실행하여 Lambda 함수 배포"
echo "2. PM2 서버 재시작"
