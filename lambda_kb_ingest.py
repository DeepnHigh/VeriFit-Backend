import json
import boto3
import logging
import os
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')
# Control-plane(관리) API는 'bedrock-agent'를 사용해야 StartIngestionJob이 존재합니다.
# KB가 us-east-1에 있으므로 Lambda 리전과 무관하게 BEDROCK_REGION(또는 기본 us-east-1)으로 강제합니다.
bedrock_agent_cp = boto3.client('bedrock-agent', region_name=os.environ.get('BEDROCK_REGION', 'us-east-1'))

def lambda_handler(event, context):
    """
    지원자 full_text를 S3에 업로드하고 Bedrock Knowledge Base 인덱싱을 트리거합니다.

    입력(JSON):
    {
      "applicant_id": "uuid",
      "job_posting_id": "uuid",
      "full_text": "...",                # 필수(권장)
      "behavior_text": "...",            # 선택
      "big5_text": "...",                 # 선택
      "s3_bucket": "my-bucket",          # 선택: 없으면 ENV 사용
      "kb_id": "kb-xxxx",                # Knowledge Base ID (ENV 또는 입력)
      "data_source_id": "ds-xxxx"        # Data Source ID (ENV 또는 입력)
    }
    """
    try:
        body = event.get('body')
        if isinstance(body, str):
            payload = json.loads(body or '{}')
        else:
            payload = event if isinstance(event, dict) else {}

        applicant_id = payload.get('applicant_id')
        job_posting_id = payload.get('job_posting_id')
        full_text = payload.get('full_text')
        behavior_text = payload.get('behavior_text')
        big5_text = payload.get('big5_text')

        if not applicant_id or not job_posting_id:
            return _resp(400, {"success": False, "error": "applicant_id, job_posting_id required"})
        if not (full_text or behavior_text or big5_text):
            return _resp(400, {"success": False, "error": "at least one of full_text, behavior_text, big5_text required"})

        bucket = payload.get('s3_bucket') or os.environ.get('KB_S3_BUCKET')
        if not bucket:
            return _resp(400, {"success": False, "error": "KB_S3_BUCKET env or s3_bucket required"})

        kb_id = payload.get('kb_id') or os.environ.get('KB_ID')
        data_source_id = payload.get('data_source_id') or os.environ.get('KB_DATA_SOURCE_ID')
        if not kb_id or not data_source_id:
            return _resp(400, {"success": False, "error": "KB_ID and KB_DATA_SOURCE_ID required"})

        # S3 키: {base_prefix}/kb/{job_posting_id}/{applicant_id}/...
        base_prefix = (payload.get('base_prefix') or os.environ.get('KB_BASE_PREFIX') or '').strip('/')
        logical_prefix = f"kb/all/{applicant_id}"
        if job_posting_id:
            logical_prefix = f"kb/{job_posting_id}/{applicant_id}"
        prefix = f"{base_prefix}/{logical_prefix}" if base_prefix else logical_prefix
        uploaded = []
        if full_text:
            key_full = f"{prefix}/full_text.txt"
            s3.put_object(Bucket=bucket, Key=key_full, Body=full_text.encode('utf-8'), ContentType='text/plain')
            uploaded.append(f"s3://{bucket}/{key_full}")
            logger.info(f"S3 업로드 완료 {uploaded[-1]}")
        if behavior_text:
            key_behavior = f"{prefix}/behavior_text.txt"
            s3.put_object(Bucket=bucket, Key=key_behavior, Body=behavior_text.encode('utf-8'), ContentType='text/plain')
            uploaded.append(f"s3://{bucket}/{key_behavior}")
            logger.info(f"S3 업로드 완료 {uploaded[-1]}")
        if big5_text:
            key_big5 = f"{prefix}/big5_text.txt"
            s3.put_object(Bucket=bucket, Key=key_big5, Body=big5_text.encode('utf-8'), ContentType='text/plain')
            uploaded.append(f"s3://{bucket}/{key_big5}")
            logger.info(f"S3 업로드 완료 {uploaded[-1]}")

        # KB 인덱싱 시작 (증분) - Control-plane 클라이언트 사용
        ingest_resp = bedrock_agent_cp.start_ingestion_job(
            knowledgeBaseId=kb_id,
            dataSourceId=data_source_id
        )
        ingestion_job = ingest_resp.get('ingestionJob', {})

        return _resp(200, {
            "success": True,
            "uploaded": uploaded,
            "ingestion_job": ingestion_job
        })

    except Exception as e:
        logger.exception("KB ingest 오류")
        return _resp(500, {"success": False, "error": str(e)})


def _resp(status, body):
    # ingestion_job 내 datetime 등 비직렬화 타입 처리
    return {"statusCode": status, "body": json.dumps(body, ensure_ascii=False, default=str)}


