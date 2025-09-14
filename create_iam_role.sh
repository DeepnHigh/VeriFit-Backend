#!/bin/bash

echo "🔐 Lambda용 IAM Role 생성 시작"

ROLE_NAME="SafeRoleForUser-seoul-ht-01"
POLICY_NAME="lambda-bedrock-policy"

# 1. Trust Policy 생성
echo "📝 Trust Policy 생성 중..."
cat > trust-policy.json << EOF
{
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
}
EOF

# 2. IAM Role 생성
echo "🆕 IAM Role 생성 중..."
aws iam create-role \
    --role-name $ROLE_NAME \
    --assume-role-policy-document file://trust-policy.json

# 3. 기본 Lambda 실행 정책 연결
echo "🔗 기본 Lambda 실행 정책 연결 중..."
aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# 4. Bedrock 정책 생성
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
                "arn:aws:bedrock:us-east-1::foundation-model/us.anthropic.claude-3-5-sonnet-20241022-v2:0"
            ]
        }
    ]
}
EOF

# 5. Bedrock 정책 생성 및 연결
echo "🔗 Bedrock 정책 생성 및 연결 중..."
aws iam create-policy \
    --policy-name $POLICY_NAME \
    --policy-document file://bedrock-policy.json

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn arn:aws:iam::$ACCOUNT_ID:policy/$POLICY_NAME

# 6. Role ARN 출력
echo "✅ IAM Role 생성 완료"
echo "📋 Role ARN: arn:aws:iam::$ACCOUNT_ID:role/$ROLE_NAME"

# 7. 정리
rm -f trust-policy.json bedrock-policy.json

echo "🎉 IAM Role 설정 완료!"
echo ""
echo "📋 다음 단계:"
echo "1. ./setup_lambda.sh 실행하여 Lambda 함수 배포"
echo "2. PM2 서버 재시작"
