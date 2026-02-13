# AI Agent Discovery Guide

**Version:** 1.2.0  
**Date:** 2026-02-12  
**Status:** Production Ready

---

## Overview

OpenClaw Hub is designed to be **fully discoverable** by AI agents without requiring hardcoded knowledge or manual configuration. This document explains how any AI agent can discover and use all Hub capabilities dynamically.

## Discovery Flow

### Step 1: Check Availability

```bash
curl http://127.0.0.1:8080/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-02-12T21:45:00",
  "version": "0.1.0"
}
```

### Step 2: Get Complete Usage Instructions

**This is the primary discovery endpoint for AI agents.**

```bash
curl http://127.0.0.1:8080/v1/usage
```

**Returns:**
- Name and version
- Documentation links (Swagger UI, ReDoc, OpenAPI)
- Getting started steps
- All capabilities with endpoints and examples
- Discovery pattern explanation
- Authentication details
- Best practices for AI agents
- Rate limits

### Step 3: Discover Specific Capabilities

Based on your needs, query domain-specific discovery endpoints:

```bash
# LLM Models
curl http://127.0.0.1:8080/v1/models
→ Lists 18 models across Ollama, OpenAI, Anthropic

# Workflows
curl http://127.0.0.1:8080/v1/workflows
→ Lists available orchestration workflows

# GitHub Capabilities
curl http://127.0.0.1:8080/v1/github/capabilities
→ Lists all GitHub operations, endpoints, rate limits

# Instagram/Social Capabilities
curl http://127.0.0.1:8080/v1/social/capabilities
→ Lists Instagram posting, upload, scheduling

# Video Generation
curl http://127.0.0.1:8080/v1/videos/capabilities
→ Shows Sora framework status and alternatives
```

### Step 4: Review OpenAPI Documentation (Optional)

For detailed schemas:

```bash
# Full OpenAPI specification
curl http://127.0.0.1:8080/openapi.json

# Or visit interactive docs in browser
# http://127.0.0.1:8080/docs (Swagger UI)
# http://127.0.0.1:8080/redoc (ReDoc)
```

### Step 5: Use the Capabilities

Now you have everything you need to make API calls!

## Example: Discovering and Using GitHub

```bash
# 1. Discover GitHub capabilities
curl http://127.0.0.1:8080/v1/github/capabilities

# Response includes:
# - List of operations (get_user, list_repos, create_issue, etc.)
# - Endpoint URLs for each operation
# - Rate limits (5000 req/hr standard, 30/min search)
# - Authentication method (Bearer token, managed by Hub)

# 2. Use a GitHub operation
curl -X POST http://127.0.0.1:8080/v1/github/repos/openclaw-community/openclaw-hub/issues \
  -H "Content-Type: application/json" \
  -d '{
    "owner": "openclaw-community",
    "repo": "openclaw-hub",
    "title": "Feature request from AI agent",
    "body": "Detailed description...",
    "labels": ["enhancement"]
  }'
```

## Example: Discovering and Generating Images

```bash
# 1. Check usage guide
curl http://127.0.0.1:8080/v1/usage | jq '.capabilities.image_generation'

# Response includes:
# - Endpoint: POST /v1/images/generations
# - Models: dall-e-2, dall-e-3
# - Max resolution: 1792x1024 (HD)

# 2. Generate an image
curl -X POST http://127.0.0.1:8080/v1/images/generations \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A photorealistic robot crab building infrastructure",
    "model": "dall-e-3",
    "size": "1792x1024",
    "quality": "hd"
  }'
```

## Discovery Pattern Principles

### 1. Progressive Disclosure
Start with high-level overview (`/v1/usage`), then drill down to specific capabilities.

### 2. Self-Documenting
Every endpoint includes:
- Clear descriptions
- Request/response schemas
- Validation rules
- Examples

### 3. Dynamic Discovery
Check capabilities at runtime instead of hardcoding assumptions. The Hub may add new features between sessions.

### 4. Single Source of Truth
`GET /v1/usage` is the canonical starting point for AI agents.

### 5. Human-Friendly Too
All discovery endpoints return human-readable JSON. Interactive docs available for humans at `/docs`.

## Integration Guidelines

### For OpenClaw Instances

Add to your `TOOLS.md` or equivalent:

```markdown
## OpenClaw Hub

**Location:** http://127.0.0.1:8080

**First time using? Start here:**
curl http://127.0.0.1:8080/v1/usage

This endpoint provides complete usage instructions for AI agents.

**Discovery Pattern:**
1. GET /v1/usage - Overview
2. GET /v1/{domain}/capabilities - Domain-specific details
3. Use the APIs

**Documentation for humans:**
http://127.0.0.1:8080/docs
```

### For Other AI Agents

1. Check if Hub is available: `GET /health`
2. Get usage instructions: `GET /v1/usage`
3. Parse the JSON response to discover capabilities
4. Make API calls based on discovered endpoints

## Capability Discovery Response Format

Each `/capabilities` endpoint returns:

```json
{
  "provider": "Provider name",
  "capabilities": ["operation1", "operation2", ...],
  "endpoints": {
    "operation1": "/v1/path/to/operation1",
    "operation2": "POST /v1/path/to/operation2"
  },
  "rate_limits": {
    "type": "limit value"
  },
  "authentication": "Description of auth (usually handled by Hub)",
  "additional_info": {...}
}
```

## Best Practices for AI Agents

1. **Always start with `/v1/usage`** - Don't assume capabilities
2. **Cache discovery responses** - Reduces API calls
3. **Check schemas in OpenAPI** - For detailed validation rules
4. **Handle missing capabilities gracefully** - Features may not be configured
5. **Respect rate limits** - Documented in capability responses
6. **Use examples as templates** - Provided in `/v1/usage`

## Error Handling

If a capability is not configured:

```json
{
  "detail": "GITHUB_TOKEN not configured"
}
```

Check the Hub's `.env` configuration and ensure required API keys are set.

## Authentication

**Important:** The Hub manages all API keys internally. Callers do not need to provide:
- OpenAI API keys
- Anthropic API keys
- GitHub tokens
- Late.dev API keys

Authentication is configured once in the Hub's `.env` file, then all callers can use the capabilities without managing credentials.

## Rate Limits

Rate limits vary by capability:

| Capability | Limit | Notes |
|------------|-------|-------|
| LLM (local) | Unlimited | Ollama on local hardware |
| LLM (cloud) | Provider-specific | OpenAI/Anthropic limits apply |
| GitHub (standard) | 5000 req/hr | Authenticated user |
| GitHub (search) | 30 req/min | Search endpoints only |
| Images | Provider-specific | OpenAI DALL-E limits |
| Instagram | Unknown | Late.dev limits |

## Support

- **GitHub Repository:** https://github.com/openclaw-community/openclaw-hub
- **Issues:** Report problems or request features
- **Documentation:** See `docs/` folder in repository
- **Interactive API Explorer:** http://127.0.0.1:8080/docs

## Changelog

### v1.2.0 (2026-02-12)
- Added `/v1/usage` endpoint for AI agent discovery
- Updated documentation with prominent discovery pattern
- Made Hub fully self-documenting

### v1.1.0 (2026-02-12)
- Added GitHub, Instagram, and image generation capabilities
- Added per-domain `/capabilities` endpoints

### v1.0.0 (2026-02-11)
- Initial release with LLM routing, workflows, and MCP

---

**For the most up-to-date information, always query `/v1/usage` when connecting to the Hub.**
