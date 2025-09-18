from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.services.application_service import ApplicationService

router = APIRouter()

@router.post("/applications")
async def create_application(payload: dict, db: Session = Depends(get_db)):
    job_posting_id = payload.get("job_posting_id")
    job_seeker_id = payload.get("job_seeker_id")

    service = ApplicationService(db)
    result = service.create_application(job_posting_id, job_seeker_id)

    if not result.get("success"):
        status = result.get("status", 400)
        raise HTTPException(status_code=status, detail=result.get("message", "요청에 실패했습니다"))

    return result
