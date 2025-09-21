from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.services.job_seeker_service import JobSeekerService
from app.services.github_service import GithubService
import logging

router = APIRouter(
    prefix="/hardskill",
    tags=["Hard Skill"]
)

logger = logging.getLogger(__name__)

@router.post("/save/{user_id}")
async def analyze_and_save_github_history(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    구직자의 GitHub 저장소를 분석하고 이력을 저장합니다.
    
    - `job_seekers` 테이블에서 저장소 URL을 가져옵니다.
    - GitHub API를 사용하여 통계(커밋, PR, 이슈, 언어)를 수집합니다.
    - 데이터를 요약합니다.
    - 요약된 내용을 `job_seekers.github_histories` JSONB 컬럼에 저장합니다.
    """
    job_seeker_service = JobSeekerService(db)
    github_service = GithubService()

    try:
        # 1. 구직자 정보와 GitHub 저장소 목록 가져오기
        job_seeker = job_seeker_service.get_applicant_profile(user_id)
        if not job_seeker:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="구직자를 찾을 수 없습니다."
            )

        repo_info = job_seeker.github_repositories
        if not repo_info or not isinstance(repo_info, dict) or "repository" not in repo_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="해당 사용자의 GitHub 저장소 정보가 없거나 데이터 형식이 올바르지 않습니다."
            )
        # repo_info는 이전에 CSV 파싱 시 {'username': <owner>, 'repository': [<urls>]} 형식으로 저장됩니다.
        repo_urls = repo_info.get("repository", [])
        repo_owner = repo_info.get("username") or repo_info.get("owner")
        # Normalize repo_owner: when CSV parsing stored a list, take the first element
        if isinstance(repo_owner, list) and len(repo_owner) > 0:
            repo_owner = repo_owner[0]
        # If it's a dict or other type, coerce to string or set to None
        if isinstance(repo_owner, dict):
            # try common keys
            repo_owner = repo_owner.get("username") or repo_owner.get("owner") or None
        if repo_owner is not None:
            try:
                repo_owner = str(repo_owner)
            except Exception:
                repo_owner = None
        if not repo_urls:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="저장소 목록이 비어있습니다."
            )

        # 2. GithubService를 사용하여 저장소 분석
        # 주어진 username(소유자)만 필터링하려면 repo_owner를 전달
        analysis_result = await github_service.analyze_repositories(repo_urls, owner_username=repo_owner)

        # 3. 결과를 job_seekers.github_histories에 저장
        job_seeker.github_histories = {"histories": analysis_result}
        db.add(job_seeker)
        db.commit()
        db.refresh(job_seeker)

        return {
            "success": True,
            "message": "GitHub 활동을 성공적으로 분석하고 저장했습니다.",
            "data": job_seeker.github_histories
        }
    finally:
        # httpx 클라이언트가 항상 닫히도록 보장
        await github_service.close()