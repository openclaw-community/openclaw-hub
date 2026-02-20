# GitHub Integration

**Status:** ✅ Complete and Production-Ready  
**Version:** v1.2.0  
**Date:** 2026-02-12

## Overview

OpenClaw Hub now includes comprehensive GitHub integration as a discoverable capability, allowing AI agents to interact with GitHub repositories, issues, pull requests, and code search through a unified REST API.

## Authentication

The integration uses a GitHub Personal Access Token stored in the `GITHUB_TOKEN` environment variable. The current token authenticates as **sageopenclawbot**.

## Capabilities

### User Operations
- **GET /v1/github/user** - Get authenticated user information

### Repository Operations
- **GET /v1/github/repos** - List repositories (for user or org)
  - Query params: `owner`, `visibility`, `sort`, `per_page`
- **GET /v1/github/repos/{owner}/{repo}** - Get repository details

### Issue Operations
- **GET /v1/github/repos/{owner}/{repo}/issues** - List issues
  - Query params: `state`, `labels`, `per_page`
- **GET /v1/github/repos/{owner}/{repo}/issues/{issue_number}** - Get specific issue
- **POST /v1/github/repos/{owner}/{repo}/issues** - Create new issue
  - Body: `title`, `body`, `labels`, `assignees`
- **PATCH /v1/github/repos/{owner}/{repo}/issues/{issue_number}** - Update issue
  - Body: `title`, `body`, `state`, `labels`

### Pull Request Operations
- **GET /v1/github/repos/{owner}/{repo}/pulls** - List pull requests
  - Query params: `state`, `per_page`
- **GET /v1/github/repos/{owner}/{repo}/pulls/{pr_number}** - Get specific PR

### Search Operations
- **GET /v1/github/search/code** - Search code across GitHub
  - Query param: `query` (GitHub search syntax)
- **GET /v1/github/search/issues** - Search issues and PRs
  - Query param: `query` (GitHub search syntax)

### Discovery
- **GET /v1/github/capabilities** - List all available GitHub capabilities

## Architecture

The integration follows the same pattern as other OpenClaw Hub integrations:

```
aigateway/
├── github/
│   ├── __init__.py
│   └── client.py          # GitHubClient - GitHub REST API wrapper
├── api/
│   └── github.py          # FastAPI endpoints
├── config.py              # Added GITHUB_TOKEN setting
└── main.py                # Registered github_router
```

## Testing

All endpoints tested successfully:

```bash
# Health check
curl http://127.0.0.1:8080/health

# Get authenticated user
curl http://127.0.0.1:8080/v1/github/user

# List openclaw-community repos
curl "http://127.0.0.1:8080/v1/github/repos?owner=openclaw-community"

# List openclaw-hub issues
curl "http://127.0.0.1:8080/v1/github/repos/openclaw-community/openclaw-hub/issues"

# Check capabilities
curl http://127.0.0.1:8080/v1/github/capabilities
```

## Rate Limits

GitHub API rate limits (authenticated):
- **Standard endpoints:** 5,000 requests/hour
- **Search endpoints:** 30 requests/minute

The client includes proper error handling for rate limit responses.

## Security

- GitHub token stored in `.env` file (never committed)
- Token included in `.gitignore` patterns
- All API requests use Bearer token authentication
- No credentials exposed in logs or error messages

## Integration with OpenClaw

OpenClaw can now discover GitHub capabilities via:

```
GET /v1/github/capabilities
```

And interact with GitHub through standard REST calls:

```python
# Example: Create an issue
POST /v1/github/repos/openclaw-community/openclaw-hub/issues
{
  "owner": "openclaw-community",
  "repo": "openclaw-hub",
  "title": "New feature request",
  "body": "Detailed description...",
  "labels": ["enhancement"]
}
```

## Next Steps

Potential enhancements:
1. Add comment management (create/update/delete comments)
2. Add webhook support for event notifications
3. Add repository management (create/update repos)
4. Add team and organization management
5. Add GitHub Actions integration (trigger workflows, get run status)
6. Add file content operations (read/write files via API)

## Related Documentation

- **GitHub REST API:** https://docs.github.com/en/rest
- **OpenClaw Hub Architecture:** docs/ARCHITECTURE.md
- **Configuration Guide:** .env.example

---

**Commit:** 7fb7d02  
**GitHub Repo:** https://github.com/openclaw-community/openclaw-hub
