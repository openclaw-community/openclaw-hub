"""GitHub API client for repository and issue management."""
from typing import Optional, List, Dict, Any
import httpx
import structlog
from ..config import settings

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
            "X-GitHub-Api-Version": "2022-11-28"
        }
    
    async def get_user(self) -> Dict[str, Any]:
        """Get authenticated user info."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/user",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def list_repos(
        self,
        owner: Optional[str] = None,
        visibility: str = "all",
        sort: str = "updated",
        per_page: int = 30
    ) -> List[Dict[str, Any]]:
        """List repositories for a user or authenticated user.
        
        Args:
            owner: Username (if None, uses authenticated user)
            visibility: "all", "public", or "private"
            sort: "created", "updated", "pushed", "full_name"
            per_page: Results per page (max 100)
        
        Returns:
            List of repository objects
        """
        if owner:
            url = f"{self.base_url}/users/{owner}/repos"
        else:
            url = f"{self.base_url}/user/repos"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=self.headers,
                params={
                    "visibility": visibility,
                    "sort": sort,
                    "per_page": per_page
                }
            )
            response.raise_for_status()
            repos = response.json()
        
        logger.info("repos_listed", count=len(repos), owner=owner or "authenticated_user")
        return repos
    
    async def get_repo(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get repository details.
        
        Args:
            owner: Repository owner
            repo: Repository name
        
        Returns:
            Repository object
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def list_issues(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        labels: Optional[List[str]] = None,
        per_page: int = 30
    ) -> List[Dict[str, Any]]:
        """List issues for a repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            state: "open", "closed", or "all"
            labels: Filter by label names
            per_page: Results per page (max 100)
        
        Returns:
            List of issue objects
        """
        params = {
            "state": state,
            "per_page": per_page
        }
        
        if labels:
            params["labels"] = ",".join(labels)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/issues",
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            issues = response.json()
        
        logger.info(
            "issues_listed",
            repo=f"{owner}/{repo}",
            count=len(issues),
            state=state
        )
        return issues
    
    async def get_issue(
        self,
        owner: str,
        repo: str,
        issue_number: int
    ) -> Dict[str, Any]:
        """Get a specific issue.
        
        Args:
            owner: Repository owner
            repo: Repository name
            issue_number: Issue number
        
        Returns:
            Issue object
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: Optional[str] = None,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create a new issue.
        
        Args:
            owner: Repository owner
            repo: Repository name
            title: Issue title
            body: Issue description (markdown)
            labels: Label names to add
            assignees: Usernames to assign
        
        Returns:
            Created issue object
        """
        payload = {"title": title}
        
        if body:
            payload["body"] = body
        if labels:
            payload["labels"] = labels
        if assignees:
            payload["assignees"] = assignees
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/repos/{owner}/{repo}/issues",
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            issue = response.json()
        
        logger.info(
            "issue_created",
            repo=f"{owner}/{repo}",
            issue_number=issue["number"],
            title=title
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
        labels: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Update an existing issue.
        
        Args:
            owner: Repository owner
            repo: Repository name
            issue_number: Issue number
            title: New title
            body: New description
            state: "open" or "closed"
            labels: Replace labels
        
        Returns:
            Updated issue object
        """
        payload = {}
        
        if title:
            payload["title"] = title
        if body:
            payload["body"] = body
        if state:
            payload["state"] = state
        if labels is not None:
            payload["labels"] = labels
        
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}",
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            issue = response.json()
        
        logger.info(
            "issue_updated",
            repo=f"{owner}/{repo}",
            issue_number=issue_number
        )
        return issue
    
    async def list_pull_requests(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        per_page: int = 30
    ) -> List[Dict[str, Any]]:
        """List pull requests for a repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            state: "open", "closed", or "all"
            per_page: Results per page (max 100)
        
        Returns:
            List of pull request objects
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/pulls",
                headers=self.headers,
                params={"state": state, "per_page": per_page}
            )
            response.raise_for_status()
            prs = response.json()
        
        logger.info(
            "pull_requests_listed",
            repo=f"{owner}/{repo}",
            count=len(prs),
            state=state
        )
        return prs
    
    async def get_pull_request(
        self,
        owner: str,
        repo: str,
        pr_number: int
    ) -> Dict[str, Any]:
        """Get a specific pull request.
        
        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
        
        Returns:
            Pull request object
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def search_code(
        self,
        query: str,
        per_page: int = 30
    ) -> Dict[str, Any]:
        """Search code across GitHub.
        
        Args:
            query: Search query (see GitHub search syntax)
            per_page: Results per page (max 100)
        
        Returns:
            Search results with items
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/search/code",
                headers=self.headers,
                params={"q": query, "per_page": per_page}
            )
            response.raise_for_status()
            results = response.json()
        
        logger.info(
            "code_searched",
            query=query,
            total_count=results.get("total_count", 0)
        )
        return results
    
    async def search_issues(
        self,
        query: str,
        per_page: int = 30
    ) -> Dict[str, Any]:
        """Search issues and pull requests across GitHub.
        
        Args:
            query: Search query (see GitHub search syntax)
            per_page: Results per page (max 100)
        
        Returns:
            Search results with items
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/search/issues",
                headers=self.headers,
                params={"q": query, "per_page": per_page}
            )
            response.raise_for_status()
            results = response.json()
        
        logger.info(
            "issues_searched",
            query=query,
            total_count=results.get("total_count", 0)
        )
        return results
