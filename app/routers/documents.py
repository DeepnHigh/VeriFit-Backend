from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.services.document_service import DocumentService

router = APIRouter()

@router.post("/docs/{user_id}")
async def upload_document(
    user_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """지원자 파일 업로드"""
    service = DocumentService(db)
    return service.upload_document(user_id, file)

@router.get("/docs/{document_id}")
async def get_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """지원자 파일 개별 조회 (다운로드)"""
    service = DocumentService(db)
    return service.get_document(document_id)

@router.delete("/docs/{document_id}")
async def delete_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """지원자 파일 개별 삭제"""
    service = DocumentService(db)
    return service.delete_document(document_id)
