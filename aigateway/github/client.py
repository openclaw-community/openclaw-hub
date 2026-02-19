"""GitHub API client for repository and issue management."""
import time
import json
from typing import Optional, List, Dict, Any
import httpx
import structlog
from ..config import settings
from ..dashboard.api_logger import log_api_call

logger = structlog.get_logger()


class GitHubClient:
    """Client for GitHub REST API v3."""

    def __init__(self):
        self.token = settings.github_token
        if not self.token:
            raise ValueError("GITHUB_TOKEN not configured")

        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def _request(
        self,
        method: str,
        path: str,
        operation: str,
        payload: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Any:
        """
        Make an instrumented HTTP request to the GitHub API.

        Measures latency, calls the upstream API, logs the result to
        api_calls regardless of success or failure, then re-raises any
        exception so callers handle errors normally.
        """
        url = f"{self.base_url}{path}"
        start = time.monotonic()
        status_code: Optional[int] = None
        success = True
        error_msg: Optional[str] = None
        request_bytes: Optional[int] = None
        response_bytes: Optional[int] = None

        try:
            kwargs: Dict = {"headers": self.headers}
            if params:
                kwargs["params"] = {k: v for k, v in params.items() if v is not None}
            if payload is not None:
                kwargs["json"] = payload
                request_bytes = len(json.dumps(payload).encode())

            async with httpx.AsyncClient() as client:
                response = await client.request(method, url, **kwargs)
                status_code = response.status_code
                response_bytes = len(response.content)
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            success = False
            error_msg = exc.response.text[:500]
            raise

        except Exception as exc:
            success = False
            error_msg = str(exc)
            raise

        finally:
            latency = (time.monotonic() - start) * 1000
            await log_api_call(
                service="github",
                operation=operation,
                endpoint=path,
                method=method.upper(),
                status_code=status_code,
                success=success,
                error=error_msg,
                latency_ms=latency,
                request_size_bytes=request_bytes,
                response_size_bytes=response_bytes,
            )

    # -------------------------------------------------------------------------
    # User
    # -------------------------------------------------------------------------

    async def get_user(self) -> Dict[str, Any]:
        """Get authenticated user info."""
        return await self._request("GET", "/user", operation="get_user")

    # -------------------------------------------------------------------------
    # Repositories
    # -------------------------------------------------------------------------

    async def list_repos(
        self,
        owner: Optional[str] = None,
        visibility: str = "all",
        sort: str = "updated",
        per_page: int = 30,
    ) -> List[Dict[str, Any]]:
        """List repositories for a user or the authenticated user."""
        path = f"/users/{owner}/repos" if owner else "/user/repos"
        repos = await self._request(
            "GET",
            path,
            operation="list_repos",
            params={"visibility": visibility, "sort": sort, "per_page": per_page},
        )
        logger.info("repos_listed", count=len(repos), owner=owner or "authenticated_user")
        return repos

    async def get_repo(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get repository details."""
        return await self._request(
            "GET", f"/repos/{owner}/{repo}", operation="get_repo"
        )

    # -------------------------------------------------------------------------
    # Issues
    # -------------------------------------------------------------------------

    async def list_issues(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        labels: Optional[List[str]] = None,
        per_page: int = 30,
    ) -> List[Dict[str, Any]]:
        """List issues for a repository."""
        params = {"state": state, "per_page": per_page}
        if labels:
            params["labels"] = ",".join(labels)

        issues = await self._request(
            "GET",
            f"/repos/{owner}/{repo}/issues",
            operation="list_issues",
            params=params,
        )
        logger.info("issues_listed", repo=f"{owner}/{repo}", count=len(issues), state=state)
        return issues

    async def get_issue(self, owner: str, repo: str, issue_number: int) -> Dict[str, Any]:
        """Get a specific issue."""
        return await self._request(
            "GET",
            f"/repos/{owner}/{repo}/issues/{issue_number}",
            operation="get_issue",
        )

    async def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: Optional[str] = None,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a new issue."""
        payload: Dict[str, Any] = {"title": title}
        if body:
            payload["body"] = body
        if labels:
            payload["labels"] = labels
        if assignees:
            payload["assignees"] = assignees

        issue = await self._request(
            "POST",
            f"/repos/{owner}/{repo}/issues",
            operation="create_issue",
            payload=payload,
        )
        logger.info(
            "issue_created",
            repo=f"{owner}/{repo}",
            issue_number=issue["number"],
            title=title,
        )
        return issue

    async def update_issue(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        title: Optional[str] = None,
        body: Optional[str] = None,
        state: Optional[str] = None,
        labels: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Update an existing issue."""
        payload: Dict[str, Any] = {}
        if title:
            payload["title"] = title
        if body:
            payload["body"] = body
        if state:
            payload["state"] = state
        if labels is not None:
            payload["labels"] = labels

        issue = await self._request(
            "PATCH",
            f"/repos/{owner}/{repo}/issues/{issue_number}",
            operation="update_issue",
            payload=payload,
        )
        logger.info("issue_updated", repo=f"{owner}/{repo}", issue_number=issue_number)
        return issue

    # -------------------------------------------------------------------------
    # Pull Requests
    # -------------------------------------------------------------------------

    async def list_pull_requests(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        per_page: int = 30,
    ) -> List[Dict[str, Any]]:
        """List pull requests for a repository."""
        prs = await self._request(
            "GET",
            f"/repos/{owner}/{repo}/pulls",
            operation="list_pull_requests",
            params={"state": state, "per_page": per_page},
        )
        logger.info("pull_requests_listed", repo=f"{owner}/{repo}", count=len(prs), state=state)
        return prs

    async def get_pull_request(
        self, owner: str, repo: str, pr_number: int
    ) -> Dict[str, Any]:
        """Get a specific pull request."""
        return await self._request(
            "GET",
            f"/repos/{owner}/{repo}/pulls/{pr_number}",
            operation="get_pull_request",
        )

    # -------------------------------------------------------------------------
    # Search
    # -------------------------------------------------------------------------

    async def search_code(self, query: str, per_page: int = 30) -> Dict[str, Any]:
        """Search code across GitHub."""
        results = await self._request(
            "GET",
            "/search/code",
            operation="search_code",
            params={"q": query, "per_page": per_page},
        )
        logger.info("code_searched", query=query, total_count=results.get("total_count", 0))
        return results

    async def search_issues(self, query: str, per_page: int = 30) -> Dict[str, Any]:
        """Search issues and pull requests across GitHub."""
        results = await self._request(
            "GET",
            "/search/issues",
            operation="search_issues",
            params={"q": query, "per_page": per_page},
        )
        logger.info("issues_searched", query=query, total_count=results.get("total_count", 0))
        return results
