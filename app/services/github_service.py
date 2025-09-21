import httpx
import asyncio
from typing import List, Dict, Any
import logging
from urllib.parse import urlparse
from app.core.config import settings

logger = logging.getLogger(__name__)

# Token은 설정에서 읽어옵니다. 없으면 무인증(제한)로 동작합니다.
_token = settings.github_token
HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "X-GitHub-Api-Version": "2022-11-28"
}
if _token:
    HEADERS["Authorization"] = f"Bearer {_token}"

class GithubService:
    def __init__(self):
        self.client = httpx.AsyncClient(headers=HEADERS, timeout=30.0)

    def _parse_repo_url(self, url: str) -> str | None:
        """GitHub URL에서 'owner/repo' 형식을 추출합니다."""
        try:
            path = urlparse(url).path
            parts = path.strip('/').split('/')
            if len(parts) >= 2 and parts[0] and parts[1]:
                return f"{parts[0]}/{parts[1]}"
            return None
        except Exception as e:
            logger.warning(f"저장소 URL 파싱 실패: {url}, 오류: {e}")
            return None

    async def _fetch_repo_data(self, repo_full_name: str) -> Dict[str, Any]:
        """단일 저장소에 대한 다양한 데이터를 가져옵니다."""
        api_base_url = "https://api.github.com"
        
        # API 호출을 병렬로 실행하기 위해 asyncio.gather 사용
        # 요청: 저장소 상세, 언어, 커밋(최신 100), PR(최신 100), 이슈(최신 100), 레포 트리(파일 목록 일부)
        tasks = {
            "details": self.client.get(f"{api_base_url}/repos/{repo_full_name}"),
            "languages": self.client.get(f"{api_base_url}/repos/{repo_full_name}/languages"),
            "commits": self.client.get(f"{api_base_url}/repos/{repo_full_name}/commits?per_page=100"),
            "prs": self.client.get(f"{api_base_url}/repos/{repo_full_name}/pulls?state=all&per_page=100"),
            "issues": self.client.get(f"{api_base_url}/repos/{repo_full_name}/issues?state=all&per_page=100"),
            # tree: 기본 브랜치의 최상위 트리(깊이 1) - 파일/디렉토리 목록
            "branches": self.client.get(f"{api_base_url}/repos/{repo_full_name}/branches"),
        }
        
        responses = await asyncio.gather(*tasks.values(), return_exceptions=True)
        results = dict(zip(tasks.keys(), responses))

        processed_data = {}
        for key, res in results.items():
            if isinstance(res, httpx.Response):
                if res.status_code == 200:
                    try:
                        processed = res.json()
                    except Exception:
                        # 일부 응답은 빈 바디이거나 streaming일 수 있으므로 원시 텍스트 보관
                        processed = res.text
                    processed_data[key] = processed
                else:
                    logger.error(f"{repo_full_name}의 {key} 데이터 가져오기 실패: 상태 코드 {res.status_code}, 내용: {res.text}")
                    processed_data[key] = None
            else:
                logger.error(f"{repo_full_name}의 {key} 데이터 가져오기 실패: {res}")
                processed_data[key] = None
        
        return processed_data

    def _summarize_repo_data(self, repo_full_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """가져온 저장소 데이터를 정리된 구조로 요약합니다."""
        details = data.get("details") or {}
        # commits/prs/issues는 API 응답으로 리스트(또는 dict/None)일 수 있음
        raw_commits = data.get("commits") or []
        raw_prs = data.get("prs") or []
        raw_issues = data.get("issues") or []

        def simplify_commits(raw_list):
            out = []
            seen = set()
            if not isinstance(raw_list, list):
                return out
            for item in raw_list:
                try:
                    sha = item.get("sha") if isinstance(item, dict) else None
                    commit = item.get("commit", {}) if isinstance(item, dict) else {}
                    message = (commit.get("message") or "").split("\n")[0]
                    author = None
                    date = None
                    # try item['commit']['author'] then item['author']
                    if isinstance(commit, dict):
                        author = commit.get("author", {}).get("name")
                        date = commit.get("author", {}).get("date")
                    if not author and isinstance(item, dict) and item.get("author"):
                        author = item["author"].get("login")

                    url = item.get("html_url") if isinstance(item, dict) else None
                    key = (sha, message, author)
                    if key in seen:
                        continue
                    seen.add(key)
                    out.append({
                        "sha": sha,
                        "message": message,
                        "author": author,
                        "date": date,
                        "url": url,
                    })
                except Exception:
                    continue
                if len(out) >= 100:
                    break
            return out

        def simplify_prs(raw_list):
            out = []
            seen = set()
            if not isinstance(raw_list, list):
                return out
            for item in raw_list:
                try:
                    number = item.get("number")
                    title = item.get("title")
                    user = item.get("user", {}).get("login") if item.get("user") else None
                    state = item.get("state")
                    created_at = item.get("created_at")
                    merged_at = item.get("merged_at") if item.get("merged_at") else None
                    url = item.get("html_url")
                    key = (number, title)
                    if key in seen:
                        continue
                    seen.add(key)
                    out.append({
                        "number": number,
                        "title": title,
                        "user": user,
                        "state": state,
                        "created_at": created_at,
                        "merged_at": merged_at,
                        "url": url,
                    })
                except Exception:
                    continue
                if len(out) >= 100:
                    break
            return out

        def simplify_issues(raw_list):
            out = []
            seen = set()
            if not isinstance(raw_list, list):
                return out
            for item in raw_list:
                try:
                    # GitHub issues API may include PRs in issues list; filter by 'pull_request' key
                    if item.get("pull_request"):
                        # skip PR entries when enumerating issues
                        continue
                    number = item.get("number")
                    title = item.get("title")
                    user = item.get("user", {}).get("login") if item.get("user") else None
                    state = item.get("state")
                    created_at = item.get("created_at")
                    closed_at = item.get("closed_at") if item.get("closed_at") else None
                    url = item.get("html_url")
                    key = (number, title)
                    if key in seen:
                        continue
                    seen.add(key)
                    out.append({
                        "number": number,
                        "title": title,
                        "user": user,
                        "state": state,
                        "created_at": created_at,
                        "closed_at": closed_at,
                        "url": url,
                    })
                except Exception:
                    continue
                if len(out) >= 100:
                    break
            return out

        commit_list = simplify_commits(raw_commits)
        pr_list = simplify_prs(raw_prs)
        issue_list = simplify_issues(raw_issues)

        # branches 응답으로 기본 브랜치 정보를 얻음
        branches = data.get("branches") or []
        default_branch = None
        if isinstance(branches, list) and len(branches) > 0:
            default_branch = branches[0].get("name") if isinstance(branches[0], dict) else None

        summary = {
            "repo_name": repo_full_name,
            "url": f"https://github.com/{repo_full_name}",
            "description": details.get("description"),
            "stars": details.get("stargazers_count"),
            "forks": details.get("forks_count"),
            "languages": data.get("languages"),
            "commit_count": len(commit_list),
            "commits": commit_list,
            "pr_count": len(pr_list),
            "prs": pr_list,
            "issue_count": len(issue_list),
            "issues": issue_list,
            "last_push": details.get("pushed_at"),
            "created_at": details.get("created_at"),
            "topics": details.get("topics", []),
            "default_branch": default_branch,
        }

        return summary

    async def analyze_repositories(self, repo_urls: List[str], owner_username: str | None = None) -> List[Dict[str, Any]]:
        """GitHub 저장소 URL 목록을 분석하고 요약 정보를 반환합니다."""
        if not repo_urls:
            return []

        repo_full_names = [self._parse_repo_url(url) for url in repo_urls]
        # owner_username이 주어지면 owner/repo 형태에서 owner가 일치하는 것만 필터
        filtered = [name for name in repo_full_names if name]
        if owner_username:
            filtered = [n for n in filtered if n.split('/')[0].lower() == owner_username.lower()]
        valid_repo_names = list(dict.fromkeys(filtered))  # 순서 유지 중복 제거

        if not valid_repo_names:
            logger.warning("유효한 GitHub 저장소 URL을 찾을 수 없습니다.")
            return []

        analysis_results = []
        for repo_name in valid_repo_names:
            try:
                raw_data = await self._fetch_repo_data(repo_name)
                summary = self._summarize_repo_data(repo_name, raw_data)
                analysis_results.append(summary)
            except Exception as e:
                logger.error(f"저장소 {repo_name} 분석 중 오류 발생: {e}")
                analysis_results.append({"repo_name": repo_name, "error": str(e)})

        return analysis_results

    async def close(self):
        """HTTP 클라이언트를 닫습니다."""
        await self.client.aclose()