"""GitHub API endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import structlog

from ..github.client import GitHubClient

logger = structlog.get_logger()

router = APIRouter(prefix="/v1")

# Global client instance
github_client: Optional[GitHubClient] = None


def get_github_client() -> GitHubClient:
    """Get or create the GitHub client instance."""
    global github_client
    if github_client is None:
        github_client = GitHubClient()
    return github_client


# Request/Response Models

class CreateIssueRequest(BaseModel):
    """Request model for creating an issue."""
    owner: str = Field(..., description="Repository owner")
    repo: str = Field(..., description="Repository name")
    title: str = Field(..., description="Issue title")
    body: Optional[str] = Field(None, description="Issue body (markdown)")
    labels: Optional[List[str]] = Field(None, description="Label names")
    assignees: Optional[List[str]] = Field(None, description="Usernames to assign")


class UpdateIssueRequest(BaseModel):
    """Request model for updating an issue."""
    owner: str = Field(..., description="Repository owner")
    repo: str = Field(..., description="Repository name")
    issue_number: int = Field(..., description="Issue number")
    title: Optional[str] = Field(None, description="New title")
    body: Optional[str] = Field(None, description="New body")
    state: Optional[str] = Field(None, description="New state (open/closed)")
    labels: Optional[List[str]] = Field(None, description="Replace labels")


# Endpoints

@router.get("/github/user")
async def get_authenticated_user():
    """Get authenticated user information."""
    try:
        client = get_github_client()
        user = await client.get_user()
        return user
    except ValueError as e:
        logger.error("github_config_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("github_user_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get user: {str(e)}")


@router.get("/github/repos")
async def list_repositories(
    owner: Optional[str] = None,
    visibility: str = "all",
    sort: str = "updated",
    per_page: int = 30
):
    """
    List repositories.
    
    - **owner**: Username (omit for authenticated user)
    - **visibility**: all, public, or private
    - **sort**: created, updated, pushed, or full_name
    - **per_page**: Results per page (max 100)
    """
    try:
        client = get_github_client()
        repos = await client.list_repos(
            owner=owner,
            visibility=visibility,
            sort=sort,
            per_page=per_page
        )
        return {"repositories": repos, "count": len(repos)}
    except ValueError as e:
        logger.error("github_config_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("github_repos_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list repos: {str(e)}")


@router.get("/github/repos/{owner}/{repo}")
async def get_repository(owner: str, repo: str):
    """Get repository details."""
    try:
        client = get_github_client()
        repo_data = await client.get_repo(owner, repo)
        return repo_data
    except Exception as e:
        logger.error("github_repo_error", owner=owner, repo=repo, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get repo: {str(e)}")


@router.get("/github/repos/{owner}/{repo}/issues")
async def list_issues(
    owner: str,
    repo: str,
    state: str = "open",
    labels: Optional[str] = None,
    per_page: int = 30
):
    """
    List issues for a repository.
    
    - **state**: open, closed, or all
    - **labels**: Comma-separated label names
    - **per_page**: Results per page (max 100)
    """
    try:
        client = get_github_client()
        label_list = labels.split(",") if labels else None
        issues = await client.list_issues(
            owner=owner,
            repo=repo,
            state=state,
            labels=label_list,
            per_page=per_page
        )
        return {"issues": issues, "count": len(issues)}
    except Exception as e:
        logger.error("github_issues_error", owner=owner, repo=repo, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list issues: {str(e)}")


@router.get("/github/repos/{owner}/{repo}/issues/{issue_number}")
async def get_issue(owner: str, repo: str, issue_number: int):
    """Get a specific issue."""
    try:
        client = get_github_client()
        issue = await client.get_issue(owner, repo, issue_number)
        return issue
    except Exception as e:
        logger.error(
            "github_issue_error",
            owner=owner,
            repo=repo,
            issue_number=issue_number,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Failed to get issue: {str(e)}")


@router.post("/github/repos/{owner}/{repo}/issues")
async def create_issue(request: CreateIssueRequest):
    """
    Create a new issue.
    
    Supports labels and assignees.
    """
    try:
        client = get_github_client()
        issue = await client.create_issue(
            owner=request.owner,
            repo=request.repo,
            title=request.title,
            body=request.body,
            labels=request.labels,
            assignees=request.assignees
        )
        return {
            "success": True,
            "issue": issue,
            "issue_number": issue["number"],
            "url": issue["html_url"]
        }
    except Exception as e:
        logger.error(
            "github_create_issue_error",
            owner=request.owner,
            repo=request.repo,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Failed to create issue: {str(e)}")


@router.patch("/github/repos/{owner}/{repo}/issues/{issue_number}")
async def update_issue(request: UpdateIssueRequest):
    """
    Update an existing issue.
    
    Can update title, body, state, and labels.
    """
    try:
        client = get_github_client()
        issue = await client.update_issue(
            owner=request.owner,
            repo=request.repo,
            issue_number=request.issue_number,
            title=request.title,
            body=request.body,
            state=request.state,
            labels=request.labels
        )
        return {
            "success": True,
            "issue": issue,
            "url": issue["html_url"]
        }
    except Exception as e:
        logger.error(
            "github_update_issue_error",
            owner=request.owner,
            repo=request.repo,
            issue_number=request.issue_number,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Failed to update issue: {str(e)}")


@router.get("/github/repos/{owner}/{repo}/pulls")
async def list_pull_requests(
    owner: str,
    repo: str,
    state: str = "open",
    per_page: int = 30
):
    """
    List pull requests for a repository.
    
    - **state**: open, closed, or all
    - **per_page**: Results per page (max 100)
    """
    try:
        client = get_github_client()
        prs = await client.list_pull_requests(
            owner=owner,
            repo=repo,
            state=state,
            per_page=per_page
        )
        return {"pull_requests": prs, "count": len(prs)}
    except Exception as e:
        logger.error("github_prs_error", owner=owner, repo=repo, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list PRs: {str(e)}")


@router.get("/github/repos/{owner}/{repo}/pulls/{pr_number}")
async def get_pull_request(owner: str, repo: str, pr_number: int):
    """Get a specific pull request."""
    try:
        client = get_github_client()
        pr = await client.get_pull_request(owner, repo, pr_number)
        return pr
    except Exception as e:
        logger.error(
            "github_pr_error",
            owner=owner,
            repo=repo,
            pr_number=pr_number,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Failed to get PR: {str(e)}")


@router.get("/github/search/code")
async def search_code(query: str, per_page: int = 30):
    """
    Search code across GitHub.
    
    Use GitHub search syntax (e.g., "repo:owner/name extension:py function")
    """
    try:
        client = get_github_client()
        results = await client.search_code(query=query, per_page=per_page)
        return results
    except Exception as e:
        logger.error("github_search_code_error", query=query, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to search code: {str(e)}")


@router.get("/github/search/issues")
async def search_issues(query: str, per_page: int = 30):
    """
    Search issues and pull requests across GitHub.
    
    Use GitHub search syntax (e.g., "repo:owner/name is:open label:bug")
    """
    try:
        client = get_github_client()
        results = await client.search_issues(query=query, per_page=per_page)
        return results
    except Exception as e:
        logger.error("github_search_issues_error", query=query, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to search issues: {str(e)}")


@router.get("/github/capabilities")
async def get_github_capabilities():
    """List available GitHub capabilities and endpoints."""
    return {
        "provider": "GitHub REST API v3",
        "capabilities": [
            "get_user",
            "list_repos",
            "get_repo",
            "list_issues",
            "get_issue",
            "create_issue",
            "update_issue",
            "list_prs",
            "get_pr",
            "search_code",
            "search_issues"
        ],
        "endpoints": {
            "user": "/v1/github/user",
            "repos": "/v1/github/repos",
            "repo_details": "/v1/github/repos/{owner}/{repo}",
            "issues": "/v1/github/repos/{owner}/{repo}/issues",
            "issue_details": "/v1/github/repos/{owner}/{repo}/issues/{issue_number}",
            "create_issue": "POST /v1/github/repos/{owner}/{repo}/issues",
            "update_issue": "PATCH /v1/github/repos/{owner}/{repo}/issues/{issue_number}",
            "pull_requests": "/v1/github/repos/{owner}/{repo}/pulls",
            "pr_details": "/v1/github/repos/{owner}/{repo}/pulls/{pr_number}",
            "search_code": "/v1/github/search/code",
            "search_issues": "/v1/github/search/issues",
            "capabilities": "/v1/github/capabilities"
        },
        "authentication": "Bearer token (GITHUB_TOKEN)",
        "rate_limits": {
            "authenticated": "5000 requests/hour",
            "search": "30 requests/minute"
        }
    }
