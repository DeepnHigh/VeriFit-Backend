import json
import boto3
import logging
import os
from typing import Dict, Any

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    AWS Lambda 함수: Bedrock 진단 및 테스트
    """
    try:
        logger.info("🔍 Bedrock 진단 시작")
        
        # 환경 변수에서 설정 가져오기
        region = os.environ.get('AWS_REGION', 'us-east-1')
        model_id = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-sonnet-20240229-v1:0')
        
        logger.info(f"📋 설정 확인 - Region: {region}, Model: {model_id}")
        
        # 1단계: AWS 자격 증명 확인
        try:
            sts_client = boto3.client('sts', region_name=region)
            identity = sts_client.get_caller_identity()
            logger.info(f"✅ AWS 자격 증명 확인됨 - Account: {identity.get('Account')}, User: {identity.get('Arn')}")
        except Exception as e:
            logger.error(f"❌ AWS 자격 증명 확인 실패: {str(e)}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'success': False,
                    'error': f'AWS 자격 증명 확인 실패: {str(e)}'
                })
            }
        
        # 2단계: Bedrock 클라이언트 초기화 테스트
        try:
            bedrock_client = boto3.client('bedrock-runtime', region_name=region)
            logger.info("✅ Bedrock 클라이언트 초기화 성공")
        except Exception as e:
            logger.error(f"❌ Bedrock 클라이언트 초기화 실패: {str(e)}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'success': False,
                    'error': f'Bedrock 클라이언트 초기화 실패: {str(e)}'
                })
            }
        
        # 3단계: 사용 가능한 모델 목록 확인
        try:
            bedrock_agent_client = boto3.client('bedrock', region_name=region)
            models_response = bedrock_agent_client.list_foundation_models()
            available_models = [model['modelId'] for model in models_response['modelSummaries']]
            logger.info(f"📋 사용 가능한 모델 수: {len(available_models)}")
            
            # Claude 모델만 필터링
            claude_models = [model for model in available_models if 'claude' in model.lower()]
            logger.info(f"🤖 Claude 모델 목록: {claude_models}")
            
            if model_id not in available_models:
                logger.error(f"❌ 모델 {model_id}가 사용 가능한 모델 목록에 없습니다")
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'success': False,
                        'error': f'모델 {model_id}를 찾을 수 없습니다',
                        'available_claude_models': claude_models
                    })
                }
            else:
                logger.info(f"✅ 모델 {model_id} 확인됨")
                
        except Exception as e:
            logger.error(f"❌ 모델 목록 조회 실패: {str(e)}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'success': False,
                    'error': f'모델 목록 조회 실패: {str(e)}'
                })
            }
        
        # 4단계: 간단한 Bedrock API 호출 테스트
        try:
            test_payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 10,
                "messages": [
                    {
                        "role": "user",
                        "content": "Hello"
                    }
                ]
            }
            
            logger.info(f"🚀 Bedrock API 호출 테스트 시작 - Model: {model_id}")
            response = bedrock_client.invoke_model(
                modelId=model_id,
                body=json.dumps(test_payload),
                contentType="application/json"
            )
            
            logger.info("✅ Bedrock API 호출 성공")
            response_body = json.loads(response['body'].read())
            content = response_body['content'][0]['text']
            logger.info(f"📝 응답 내용: {content}")
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'success': True,
                    'message': 'Bedrock 진단 완료',
                    'region': region,
                    'model_id': model_id,
                    'available_claude_models': claude_models,
                    'test_response': content
                })
            }
            
        except Exception as e:
            logger.error(f"❌ Bedrock API 호출 실패: {str(e)}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'success': False,
                    'error': f'Bedrock API 호출 실패: {str(e)}',
                    'region': region,
                    'model_id': model_id,
                    'available_claude_models': claude_models
                })
            }
        
    except Exception as e:
        logger.error(f"❌ 진단 중 예상치 못한 오류: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': f'진단 중 예상치 못한 오류: {str(e)}'
            })
        }
