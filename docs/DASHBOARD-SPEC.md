# OpenClaw Hub Dashboard — Implementation Specification

**Version:** 1.0  
**Date:** February 18, 2026  
**Status:** Ready for implementation  
**Repository:** https://github.com/openclaw-community/openclaw-hub

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Prerequisites and Existing Architecture](#2-prerequisites-and-existing-architecture)
3. [Implementation Phases and GitHub Workflow](#3-implementation-phases-and-github-workflow)
4. [Phase 1: Database Schema and Data Layer](#4-phase-1-database-schema-and-data-layer)
5. [Phase 2: Dashboard API Endpoints](#5-phase-2-dashboard-api-endpoints)
6. [Phase 3: Static File Serving and Dashboard HTML](#6-phase-3-static-file-serving-and-dashboard-html)
7. [Phase 4: Connection Management (CRUD)](#7-phase-4-connection-management-crud)
8. [Phase 5: Cost Configuration and Budget Alerts](#8-phase-5-cost-configuration-and-budget-alerts)
9. [Frontend Specification — Complete Visual and Functional Detail](#9-frontend-specification--complete-visual-and-functional-detail)
10. [Service Template System — Complete Reference](#10-service-template-system--complete-reference)
11. [Security Considerations](#11-security-considerations)
12. [Testing Checklist](#12-testing-checklist)
13. [Documentation Updates](#13-documentation-updates)
14. [Future Work (Out of Scope)](#14-future-work-out-of-scope)
15. [Appendix A: UI Prototype Reference (JSX)](#15-appendix-a-ui-prototype-reference-jsx)

---

## 1. Project Overview

### What We Are Building

A web-based dashboard for OpenClaw Hub, accessible at `http://127.0.0.1:8080/` when the Hub server is running. The dashboard provides:

1. **Overview page** — Summary stats (tokens today, requests, estimated cost, active connections), token usage charts by day/week/month, request distribution pie chart, and connection health status.
2. **Connections page** — Full CRUD management for all service connections (LLM providers, media APIs, git platforms, gateways, local services). Each connection type has different authentication requirements (API key, token/PAT, credentials file, or none). A template-driven "Add Connection" flow adapts the form fields to the selected service type.
3. **Costs page** — Per-model cost-per-token configuration (stored locally), budget limits (daily/weekly/monthly) with progress bars and threshold alerts, and an estimated cost over time chart.
4. **Activity page** — A scrollable feed of recent API requests showing timestamp, model, service, token counts, cost, latency, and status.

### Why We Are Building It

- Hub already logs all requests to SQLite with token counts, cost, and latency. This data is currently only accessible via raw SQL queries.
- A dashboard makes Hub immediately understandable to non-developers and potential contributors.
- Connection management via the UI eliminates the need to manually edit `.env` and YAML config files.
- No other tool in the OpenClaw/NanoClaw ecosystem offers visual cost and usage analytics for multi-provider AI operations.

### Architectural Decisions

- **Single-file HTML dashboard** — No build step, no npm, no React. One `index.html` file with embedded CSS and JavaScript. This eliminates frontend toolchain complexity.
- **Chart.js from CDN** — Loaded from `https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js`. No bundled JS dependencies.
- **FastAPI serves everything** — The existing FastAPI app serves both the API and the dashboard. No separate frontend server.
- **JSON file storage for config** — Cost configuration and budget limits are stored in `dashboard_config.json` alongside the SQLite database. Connection credentials continue to be managed through `.env` and the provider manager.
- **No new Python dependencies** — FastAPI already includes `StaticFiles` and `HTMLResponse` support. `aiofiles` may be needed for async static file serving (check if already in requirements.txt; add if not).

---

## 2. Prerequisites and Existing Architecture

### Repository Structure (Current)

```
openclaw-hub/
├── .github/
├── aigateway/
│   ├── api/
│   │   └── completions.py       # /v1/chat/completions endpoint
│   ├── providers/
│   │   ├── base.py              # Abstract provider interface
│   │   ├── ollama.py            # Ollama provider
│   │   ├── openai.py            # OpenAI provider
│   │   ├── anthropic.py         # Anthropic provider
│   │   └── manager.py           # Provider routing logic
│   ├── storage/
│   │   ├── database.py          # SQLAlchemy setup
│   │   └── models.py            # Request/Workflow ORM models
│   ├── orchestration/           # Workflow engine
│   ├── mcp/                     # MCP integration
│   ├── config.py                # Settings management
│   └── main.py                  # FastAPI application entry point
├── docs/
├── tests/
├── workflows/
├── .env.example
├── requirements.txt
├── README.md
├── CHANGELOG.md
├── STATUS.md
└── ... (other docs)
```

### Existing Database

Hub uses SQLite with SQLAlchemy. The database file is `aigateway.db` in the project root. The existing `requests` table contains (at minimum):

- `id` — Primary key
- `model` — Model name string (e.g., `gpt-4o-mini`, `claude-sonnet`, `qwen2.5:32b-instruct`)
- `provider` — Provider name string (e.g., `openai`, `anthropic`, `ollama`)
- `prompt_tokens` — Integer, input token count
- `completion_tokens` — Integer, output token count
- `cost_usd` — Float, cost in USD
- `latency_ms` — Float/Integer, response time in milliseconds
- `status` — String, request status (e.g., `success`, `error`)
- `created_at` — DateTime, when the request was made

**IMPORTANT:** Before implementing, the developer MUST inspect the actual schema by running:
```bash
sqlite3 aigateway.db ".schema requests"
```
and adapt column names if they differ from the above. The above is inferred from the README query example (`SELECT model, SUM(cost_usd) as total_cost, COUNT(*) as requests FROM requests GROUP BY model;`). The actual column names in `models.py` are authoritative.

### Existing Server

- FastAPI app is defined in `aigateway/main.py`
- Server runs on `127.0.0.1:8080` via uvicorn
- Swagger docs are available at `http://127.0.0.1:8080/docs`
- The app already has 27 endpoints

### Existing Config

- API keys are stored in `.env` file
- Settings are managed by `aigateway/config.py` (likely using Pydantic Settings or similar)
- Provider registration and routing is handled by `aigateway/providers/manager.py`

---

## 3. Implementation Phases and GitHub Workflow

### Branching Strategy

Create a feature branch from `main`:
```
git checkout -b feature/dashboard
```

All work happens on this branch. When complete, open a single PR to `main` titled:
```
feat: Add web dashboard with connection management, usage analytics, and cost tracking
```

Alternatively, if the maintainer prefers smaller PRs, split into the phases below. Each phase builds on the previous one and is independently testable.

### Phase Overview

| Phase | Branch Name | Description | New Files | Modified Files |
|-------|------------|-------------|-----------|----------------|
| 1 | `feature/dashboard-data` | Database schema additions + data layer | `aigateway/dashboard/data.py`, `aigateway/dashboard/__init__.py` | `aigateway/storage/models.py`, `aigateway/storage/database.py` |
| 2 | `feature/dashboard-api` | Dashboard REST API endpoints | `aigateway/api/dashboard.py` | `aigateway/main.py` |
| 3 | `feature/dashboard-ui` | HTML/CSS/JS dashboard frontend | `aigateway/static/index.html` | `aigateway/main.py`, `requirements.txt` (maybe) |
| 4 | `feature/dashboard-connections` | Connection CRUD (add/edit/delete/toggle) | (extends Phase 2 and 3 files) | `aigateway/api/dashboard.py`, `aigateway/static/index.html` |
| 5 | `feature/dashboard-costs` | Cost config, budget limits, alerts | (extends Phase 2 and 3 files) | `aigateway/api/dashboard.py`, `aigateway/static/index.html` |

If doing a single PR, all phases are combined into `feature/dashboard`.

### Final Repository Structure (After All Phases)

```
openclaw-hub/
├── aigateway/
│   ├── api/
│   │   ├── completions.py          # (existing, unchanged)
│   │   └── dashboard.py            # NEW — all dashboard API routes
│   ├── dashboard/
│   │   ├── __init__.py              # NEW
│   │   └── data.py                  # NEW — data access layer for dashboard queries
│   ├── providers/                   # (existing, unchanged)
│   ├── storage/
│   │   ├── database.py              # MODIFIED — add new tables
│   │   └── models.py               # MODIFIED — add new ORM models
│   ├── static/
│   │   └── index.html               # NEW — single-file dashboard
│   ├── config.py                    # (existing, may need minor additions)
│   └── main.py                      # MODIFIED — mount static files, add dashboard routes
├── dashboard_config.json            # NEW — cost config + budget limits (created at runtime)
└── ... (everything else unchanged)
```

---

## 4. Phase 1: Database Schema and Data Layer

### 4.1 New SQLAlchemy Models

Add to `aigateway/storage/models.py`:

#### Table: `connections`

Stores all configured service connections.

```python
class Connection(Base):
    __tablename__ = "connections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)              # Display name, e.g. "Production OpenAI"
    service = Column(String, nullable=False)            # Template key, e.g. "openai", "elevenlabs", "github", "custom"
    category = Column(String, nullable=False)           # Category string, e.g. "LLM", "Media / Audio", "Git / DevOps"
    base_url = Column(String, default="")               # API endpoint URL
    api_key_encrypted = Column(String, default="")      # Encrypted API key (see security section)
    token_encrypted = Column(String, default="")        # Encrypted token/PAT
    cred_path = Column(String, default="")              # Path to credentials file
    enabled = Column(Boolean, default=True)             # Whether this connection is active
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
```

**Important notes on credential storage:**
- API keys and tokens MUST NOT be stored in plaintext in the database.
- Use Fernet symmetric encryption from the `cryptography` library. The encryption key is derived from a secret stored in `.env` as `DASHBOARD_SECRET_KEY`.
- If `DASHBOARD_SECRET_KEY` is not set in `.env`, generate one on first run and append it to `.env`, then print a warning to the console.
- The `cryptography` library MUST be added to `requirements.txt`.
- For display in the dashboard, credentials are masked: show only the first 4 and last 4 characters (e.g., `sk-pr...d3Km`). The full decrypted value is NEVER returned in any API response.

#### Table: `cost_configs`

Stores per-model cost-per-token configuration.

```python
class CostConfig(Base):
    __tablename__ = "cost_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model = Column(String, nullable=False, unique=True)  # Model name pattern
    provider = Column(String, nullable=False)              # Provider/service key
    input_cost_per_million = Column(Float, default=0.0)    # USD per 1M input tokens
    output_cost_per_million = Column(Float, default=0.0)   # USD per 1M output tokens
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
```

#### Table: `budget_limits`

Stores budget thresholds. This table has at most one row.

```python
class BudgetLimit(Base):
    __tablename__ = "budget_limits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    daily_limit_usd = Column(Float, default=5.0)
    weekly_limit_usd = Column(Float, default=25.0)
    monthly_limit_usd = Column(Float, default=80.0)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
```

### 4.2 Database Migration

In `aigateway/storage/database.py`, ensure that `Base.metadata.create_all(bind=engine)` is called at startup. Since Hub uses SQLAlchemy with `create_all`, new tables are created automatically if they don't exist. No migration framework (Alembic) is needed for this phase.

**Test:** After starting the server, run:
```bash
sqlite3 aigateway.db ".tables"
```
Expected output should include `connections`, `cost_configs`, and `budget_limits` alongside the existing `requests` table.

### 4.3 Data Access Layer

Create `aigateway/dashboard/__init__.py` (empty file) and `aigateway/dashboard/data.py`.

`data.py` provides functions that the API endpoints will call. Each function takes a database session and returns data.

```python
# aigateway/dashboard/data.py

"""
Data access layer for dashboard queries.
All functions take a SQLAlchemy session and return dictionaries or lists.
"""

from datetime import datetime, timedelta
from sqlalchemy import func, desc
from aigateway.storage.models import Request, Connection, CostConfig, BudgetLimit


def get_token_usage_daily(db, days=30):
    """
    Returns token usage aggregated by day and provider for the last N days.
    
    Returns:
        list of dicts: [{"date": "2026-02-18", "provider": "openai", "total_tokens": 45230}, ...]
    """
    since = datetime.utcnow() - timedelta(days=days)
    # Query the requests table, GROUP BY date and provider
    # Use func.date() for SQLite date extraction from created_at
    # SUM prompt_tokens + completion_tokens as total_tokens
    # ORDER BY date ASC
    pass  # Implement


def get_token_usage_weekly(db, weeks=12):
    """
    Returns token usage aggregated by ISO week and provider for the last N weeks.
    
    Returns:
        list of dicts: [{"week": "2026-W07", "provider": "openai", "total_tokens": 312400}, ...]
    """
    pass  # Implement


def get_token_usage_monthly(db, months=6):
    """
    Returns token usage aggregated by month and provider for the last N months.
    
    Returns:
        list of dicts: [{"month": "2026-02", "provider": "openai", "total_tokens": 1245000}, ...]
    """
    pass  # Implement


def get_request_stats_24h(db):
    """
    Returns aggregate stats for the last 24 hours.
    
    Returns:
        dict: {
            "total_requests": 1237,
            "total_errors": 10,
            "total_prompt_tokens": 489200,
            "total_completion_tokens": 198400,
            "total_cost_usd": 2.47,
            "by_provider": {
                "openai": {"requests": 234, "errors": 0, "tokens": 189000, "cost_usd": 1.23},
                "anthropic": {"requests": 156, "errors": 8, "tokens": 124000, "cost_usd": 0.98},
                "ollama": {"requests": 847, "errors": 2, "tokens": 376200, "cost_usd": 0.0}
            }
        }
    """
    pass  # Implement


def get_recent_requests(db, limit=50):
    """
    Returns the most recent N requests, ordered by created_at DESC.
    
    Returns:
        list of dicts: [{
            "id": 1,
            "created_at": "2026-02-18T14:32:07Z",
            "model": "gpt-4o-mini",
            "provider": "openai",
            "prompt_tokens": 980,
            "completion_tokens": 320,
            "cost_usd": 0.0003,
            "latency_ms": 450,
            "status": "success"
        }, ...]
    """
    pass  # Implement


def get_connections(db):
    """
    Returns all connections with status info.
    Credentials are returned MASKED (first 4 + last 4 chars only).
    
    Returns:
        list of dicts: [{
            "id": 1,
            "name": "OpenAI",
            "service": "openai",
            "category": "LLM",
            "base_url": "https://api.openai.com/v1",
            "api_key_masked": "sk-pr...d3Km",
            "token_masked": "",
            "cred_path": "",
            "enabled": true,
            "status": "healthy",        # computed from recent request success/failure
            "latency_avg_ms": 320,      # avg latency from last 10 requests
            "requests_24h": 234,        # count from requests table
            "errors_24h": 0             # count of errors from requests table
        }, ...]
    """
    pass  # Implement


def get_cost_configs(db):
    """Returns all cost configurations."""
    pass  # Implement


def get_budget_limits(db):
    """Returns current budget limits. Creates default row if none exists."""
    pass  # Implement


def get_estimated_costs(db, period="daily"):
    """
    Calculates estimated costs by joining request token counts with cost_configs.
    Falls back to the cost_usd stored in the requests table if no cost_config exists.
    
    Args:
        period: "daily" (today), "weekly" (last 7 days), "monthly" (last 30 days)
    
    Returns:
        dict: {"estimated_cost_usd": 4.27, "period": "daily"}
    """
    pass  # Implement
```

**Note to implementing developer:** The function signatures and return formats above are the contract that the API endpoints depend on. You MUST return data in exactly these shapes. The function bodies need to be implemented with proper SQLAlchemy queries.

---

## 5. Phase 2: Dashboard API Endpoints

### 5.1 Create `aigateway/api/dashboard.py`

This file defines a FastAPI `APIRouter` with all dashboard endpoints. Every endpoint is prefixed with `/api/dashboard`.

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])
```

### 5.2 Endpoint Specification

All endpoints return JSON. All endpoints use GET except where specified.

#### `GET /api/dashboard/stats`

Returns overview statistics for the dashboard home page.

**Response (200):**
```json
{
  "tokens_today": 134520,
  "requests_24h": 1237,
  "errors_24h": 10,
  "estimated_daily_cost_usd": 4.27,
  "active_connections": 4,
  "total_connections": 6,
  "budget": {
    "daily_limit": 5.00,
    "daily_spent": 4.27,
    "daily_pct": 85.4,
    "weekly_limit": 25.00,
    "weekly_spent": 22.10,
    "weekly_pct": 88.4,
    "monthly_limit": 80.00,
    "monthly_spent": 67.30,
    "monthly_pct": 84.1
  }
}
```

#### `GET /api/dashboard/usage?period=daily`

Returns token usage time series for charts.

**Query parameters:**
- `period` — `daily` (default), `weekly`, or `monthly`

**Response (200):**
```json
{
  "period": "daily",
  "data": [
    {
      "date": "2026-01-20",
      "by_provider": {
        "ollama": 82340,
        "openai": 23100,
        "anthropic": 18900
      },
      "total": 124340
    },
    ...
  ]
}
```

#### `GET /api/dashboard/requests?limit=50`

Returns recent requests for the activity feed.

**Query parameters:**
- `limit` — Number of requests to return (default: 50, max: 200)

**Response (200):**
```json
{
  "requests": [
    {
      "id": 1,
      "created_at": "2026-02-18T14:32:07Z",
      "model": "gpt-4o-mini",
      "provider": "openai",
      "prompt_tokens": 980,
      "completion_tokens": 320,
      "cost_usd": 0.0003,
      "latency_ms": 450,
      "status": "success"
    },
    ...
  ]
}
```

#### `GET /api/dashboard/connections`

Returns all configured connections with masked credentials and health status.

**Response (200):**
```json
{
  "connections": [
    {
      "id": 1,
      "name": "OpenAI",
      "service": "openai",
      "category": "LLM",
      "base_url": "https://api.openai.com/v1",
      "api_key_masked": "sk-pr...d3Km",
      "token_masked": "",
      "cred_path": "",
      "enabled": true,
      "status": "healthy",
      "latency_avg_ms": 320,
      "requests_24h": 234,
      "errors_24h": 0,
      "last_success": "2026-02-18T14:27:00Z"
    },
    ...
  ]
}
```

#### `POST /api/dashboard/connections`

Creates a new connection. Validates by sending a lightweight test request to the provider.

**Request body:**
```json
{
  "name": "ElevenLabs",
  "service": "elevenlabs",
  "category": "Media / Audio",
  "base_url": "https://api.elevenlabs.io/v1",
  "api_key": "el-actual-key-here",
  "token": "",
  "cred_path": ""
}
```

**Response (201):**
```json
{
  "id": 7,
  "name": "ElevenLabs",
  "service": "elevenlabs",
  "message": "Connection created and validated successfully"
}
```

**Response (400) — Validation failed:**
```json
{
  "detail": "Connection validation failed: 401 Unauthorized. Check your API key."
}
```

#### `PUT /api/dashboard/connections/{id}`

Updates an existing connection. Only the fields provided in the request body are updated. If `api_key` or `token` is an empty string, the existing value is kept.

**Request body (partial update):**
```json
{
  "name": "Production OpenAI",
  "base_url": "https://api.openai.com/v1",
  "api_key": ""
}
```

**Response (200):**
```json
{
  "id": 2,
  "name": "Production OpenAI",
  "message": "Connection updated successfully"
}
```

#### `DELETE /api/dashboard/connections/{id}`

Deletes a connection permanently.

**Response (200):**
```json
{
  "message": "Connection 'ElevenLabs' deleted"
}
```

#### `PATCH /api/dashboard/connections/{id}/toggle`

Toggles a connection's enabled/disabled state.

**Response (200):**
```json
{
  "id": 6,
  "enabled": false,
  "message": "Connection 'Sora 2 Pro' disabled"
}
```

#### `GET /api/dashboard/costs`

Returns all cost configurations.

**Response (200):**
```json
{
  "costs": [
    {
      "id": 1,
      "model": "gpt-4o-mini",
      "provider": "openai",
      "input_cost_per_million": 0.15,
      "output_cost_per_million": 0.60
    },
    ...
  ]
}
```

#### `PUT /api/dashboard/costs/{id}`

Updates a cost configuration.

**Request body:**
```json
{
  "input_cost_per_million": 0.15,
  "output_cost_per_million": 0.60
}
```

**Response (200):**
```json
{
  "id": 1,
  "message": "Cost config updated"
}
```

#### `POST /api/dashboard/costs`

Creates a new cost configuration entry.

**Request body:**
```json
{
  "model": "eleven_multilingual_v2",
  "provider": "elevenlabs",
  "input_cost_per_million": 0.30,
  "output_cost_per_million": 0.0
}
```

**Response (201):**
```json
{
  "id": 7,
  "message": "Cost config created"
}
```

#### `GET /api/dashboard/budget`

Returns current budget limits.

**Response (200):**
```json
{
  "daily_limit_usd": 5.00,
  "weekly_limit_usd": 25.00,
  "monthly_limit_usd": 80.00
}
```

#### `PUT /api/dashboard/budget`

Updates budget limits.

**Request body:**
```json
{
  "daily_limit_usd": 10.00,
  "weekly_limit_usd": 50.00,
  "monthly_limit_usd": 150.00
}
```

**Response (200):**
```json
{
  "message": "Budget limits updated"
}
```

#### `GET /api/dashboard/health`

Returns health status of all enabled connections. For each connection, attempts a lightweight test (e.g., list models for LLM providers, a simple GET for others).

**Response (200):**
```json
{
  "connections": [
    {"id": 1, "name": "Ollama (Local)", "status": "healthy", "latency_ms": 12},
    {"id": 2, "name": "OpenAI", "status": "healthy", "latency_ms": 340},
    {"id": 3, "name": "Anthropic", "status": "degraded", "latency_ms": 2100}
  ]
}
```

Health status logic:
- `healthy` — Last request succeeded AND average latency < 2000ms
- `degraded` — Last request succeeded BUT average latency >= 2000ms, OR error rate > 5% in last 24h
- `error` — Last request failed OR connection unreachable

### 5.3 Register Routes in `main.py`

In `aigateway/main.py`, add:

```python
from aigateway.api.dashboard import router as dashboard_router

app.include_router(dashboard_router)
```

**Test after Phase 2:**
```bash
# Start the server
uvicorn aigateway.main:app --host 127.0.0.1 --port 8080 --reload

# Test stats endpoint
curl http://127.0.0.1:8080/api/dashboard/stats

# Test connections endpoint
curl http://127.0.0.1:8080/api/dashboard/connections

# Test budget endpoint
curl http://127.0.0.1:8080/api/dashboard/budget

# Verify in Swagger docs
# Navigate to http://127.0.0.1:8080/docs
# All /api/dashboard/* endpoints should appear under the "dashboard" tag
```

---

## 6. Phase 3: Static File Serving and Dashboard HTML

### 6.1 Configure Static File Serving in `main.py`

Add static file mounting to `aigateway/main.py`. This MUST be added AFTER all API route registrations to avoid the static file handler intercepting API requests.

```python
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
import os

# Serve the dashboard at the root URL
@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    dashboard_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    return FileResponse(dashboard_path)

# Serve any additional static assets (CSS, JS, images if added later)
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")
```

**CRITICAL:** The `app.mount("/static", ...)` line MUST come AFTER all `app.include_router(...)` calls. FastAPI processes routes in order, and a mount at `/` would catch all requests.

**CRITICAL:** Check if `aiofiles` is in `requirements.txt`. If not, add it — `StaticFiles` requires it for async file serving:
```
aiofiles>=23.0
```

### 6.2 Create `aigateway/static/index.html`

This is the single-file dashboard. It contains ALL HTML, CSS, and JavaScript in one file. External dependencies are loaded from CDN only.

**CDN dependencies to include in `<head>`:**
```html
<!-- Chart.js -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>

<!-- Google Fonts -->
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
```

No other external dependencies. No Tailwind, no React, no npm packages.

**The HTML file structure must be:**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OpenClaw Hub Dashboard</title>
    <!-- CDN links here -->
    <style>
        /* All CSS here — see Section 9 for complete style specification */
    </style>
</head>
<body>
    <!-- Header -->
    <!-- Sidebar navigation -->
    <!-- Main content area (4 views toggled by JS) -->
    <!-- Modal overlay (hidden by default) -->

    <script>
        /* All JavaScript here — see sections below for complete behavior specification */
    </script>
</body>
</html>
```

### 6.3 JavaScript Architecture

The JavaScript section of `index.html` should be organized as follows:

```javascript
// ==========================================
// 1. CONSTANTS — colors, service templates
// ==========================================

// ==========================================
// 2. STATE — current view, data caches
// ==========================================

// ==========================================
// 3. API FUNCTIONS — fetch wrappers for each endpoint
// ==========================================

// ==========================================
// 4. RENDER FUNCTIONS — one per view/component
// ==========================================

// ==========================================
// 5. CHART FUNCTIONS — Chart.js initialization and updates
// ==========================================

// ==========================================
// 6. EVENT HANDLERS — button clicks, form submissions, navigation
// ==========================================

// ==========================================
// 7. INITIALIZATION — on DOMContentLoaded, load data and render
// ==========================================
```

**Data fetching pattern:**
```javascript
async function fetchStats() {
    try {
        const response = await fetch('/api/dashboard/stats');
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error('Failed to fetch stats:', error);
        return null;
    }
}
```

Every API call must have try/catch error handling. On failure, the UI should display a subtle error message (e.g., a red banner at the top of the content area) rather than breaking.

**View switching pattern:**
```javascript
function showView(viewName) {
    // Hide all view containers
    document.querySelectorAll('.view-content').forEach(el => el.style.display = 'none');
    // Show the selected view
    document.getElementById(`view-${viewName}`).style.display = 'block';
    // Update sidebar active state
    document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));
    document.querySelector(`[data-view="${viewName}"]`).classList.add('active');
    // Refresh data for the selected view
    refreshView(viewName);
}
```

**Test after Phase 3:**
1. Start the server: `uvicorn aigateway.main:app --host 127.0.0.1 --port 8080 --reload`
2. Navigate to `http://127.0.0.1:8080/` in a browser
3. Verify: The dashboard loads with sidebar navigation showing Overview, Connections, Costs, Activity
4. Verify: Clicking sidebar items switches the main content area
5. Verify: The overview page shows stat cards and charts (they may show zeros or empty states if no request data exists yet)
6. Verify: `http://127.0.0.1:8080/docs` still works (Swagger UI is not broken)
7. Verify: `http://127.0.0.1:8080/health` still works (existing health endpoint is not broken)
8. Verify: `http://127.0.0.1:8080/v1/chat/completions` still works (existing API is not broken)

---

## 7. Phase 4: Connection Management (CRUD)

### 7.1 Service Template System

The Add Connection flow uses a template system that determines which form fields are shown. The complete template definitions are in Section 10. The key concept:

Each service template defines:
- `name` — Display name
- `category` — Category grouping (LLM, Media / Audio, Media / Video, Git / DevOps, Data, Gateway, Custom)
- `fields` — Which credential fields this service needs: `baseUrl`, `apiKey`, `token`, `credPath` (each true/false)
- `defaults` — Pre-filled values (e.g., base URL)
- `hint` — Help text shown to the user
- `color` — Hex color for the service badge and icon

The "Custom" template has all fields set to true, but with toggle buttons that let the user enable/disable each field.

### 7.2 Add Connection Flow (Two-Step Modal)

**Step 1: Service Picker**

When the user clicks "Add Connection", a modal opens showing:
1. A search input at the top that filters the service list
2. Services grouped by category in a 2-column grid
3. Each service is a clickable card showing: icon, name, one-line description

Category display order:
1. LLM
2. LLM (Local)
3. Media / Audio
4. Media / Video
5. Git / DevOps
6. Data
7. Gateway
8. Custom

Clicking a service card advances to Step 2.

**Step 2: Configure**

The form adapts based on the selected service template:
1. A colored banner showing the selected service name, icon, and hint text
2. "Connection Name" text input (always shown, pre-filled with service name)
3. Dynamic credential fields based on the template's `fields` definition:
   - If `fields.baseUrl` is true: Show "Base URL" input, pre-filled with `defaults.baseUrl`
   - If `fields.apiKey` is true: Show "API Key" input (type=password), with hint "stored locally, never transmitted except to this provider"
   - If `fields.token` is true: Show "Token / Personal Access Token" input (type=password), with context-specific placeholder (e.g., `ghp_...` for GitHub, `glpat-...` for GitLab)
   - If `fields.credPath` is true: Show "Credentials File Path" input, with hint "Absolute path to the credentials file on the Hub host"
4. For the "Custom" service type ONLY: Show toggle buttons for each field type so the user can enable/disable fields
5. A note: "Hub will validate this connection with a test request before saving."
6. "← Back" button (returns to Step 1), "Cancel" button, "Add Connection" button

On submit, POST to `/api/dashboard/connections`. On success, close the modal and refresh the connections list. On failure, show the error message inline in the modal.

### 7.3 Edit Connection Modal

Clicking "Edit" on a connection card opens a modal with:
1. A colored banner showing the service type
2. "Connection Name" — editable
3. "Base URL" — editable (only if the service template has `fields.baseUrl`)
4. "Update API Key" — password input with placeholder "Enter new key to replace current (leave blank to keep)" and hint showing the current masked value (only if the service template has `fields.apiKey`)
5. "Update Token / PAT" — same pattern as API Key (only if `fields.token`)
6. "Credentials File Path" — editable (only if `fields.credPath`)
7. Warning: "Changing credentials will trigger a connection validation test."
8. "Cancel" and "Save Changes" buttons

On submit, PUT to `/api/dashboard/connections/{id}`. Empty credential fields mean "keep existing."

### 7.4 Delete Connection

Clicking the trash icon on a connection card shows an inline confirmation bar (not a modal):
- Red background with text: "Remove {name}? This cannot be undone."
- "Cancel" button (dismisses the bar)
- "Remove" button (red, calls DELETE `/api/dashboard/connections/{id}`)

### 7.5 Toggle Connection

Clicking "Disable"/"Enable" calls PATCH `/api/dashboard/connections/{id}/toggle`. The card immediately updates its opacity (0.5 for disabled) and status shows "OFFLINE".

### 7.6 Credential Visibility Toggle

Each credential field on a connection card has an eye icon. Clicking it:
- For the prototype/v1: Simply toggles between the masked value and a slightly less masked version (e.g., showing the first 6 and last 4 characters). The FULL key is NEVER shown in the UI.
- Requires the auth state to be active (see Section 11).

**Test after Phase 4:**
1. Navigate to the Connections page
2. Click "Add Connection" — verify the service picker modal appears with categories and search
3. Select "ElevenLabs" — verify only "Connection Name" and "API Key" fields appear (no Base URL, no Token, no Cred Path)
4. Select "GitHub" — verify only "Connection Name" and "Token / PAT" fields appear
5. Select "GitLab" — verify "Connection Name", "Base URL", and "Token / PAT" fields appear
6. Select "Ollama (Local)" — verify only "Connection Name" and "Base URL" fields appear
7. Select "Custom" — verify toggle buttons appear for all field types
8. Fill in a test connection and submit — verify it appears in the list
9. Click "Edit" on a connection — verify the correct fields are shown for that service type
10. Click "Disable" — verify the card dims and shows "OFFLINE"
11. Click the trash icon — verify the inline confirmation appears
12. Click "Remove" — verify the connection disappears

---

## 8. Phase 5: Cost Configuration and Budget Alerts

### 8.1 Cost Configuration Table

The Costs page shows a table of all configured cost-per-token rates. Each row has:
- Model name (monospace font)
- Provider/service badge
- Input cost per 1M tokens (show "FREE" in green if $0)
- Output cost per 1M tokens (show "FREE" in green if $0)
- "Edit" button

Clicking "Edit" opens a modal with:
- Model name (read-only)
- Input cost input (number, monospace)
- Output cost input (number, monospace)
- "Cancel" and "Save" buttons

### 8.2 Budget Progress Bars

Three cards showing Daily, Weekly, and Monthly budgets:
- Left: Budget label
- Right: Percentage used (colored: green < 70%, yellow 70-90%, red > 90%)
- Large number: Amount spent (monospace)
- Smaller text: "/ $X.XX" limit
- Progress bar at bottom (6px height, color matches percentage)

Budget amounts are calculated from request data + cost configs. If no cost config exists for a model, use the `cost_usd` value from the requests table.

### 8.3 Budget Alert Banner

On the Overview page, if any budget exceeds 70%, show a warning banner at the top:
- Yellow background + border if 70-90%
- Red background + border if > 90%
- Alert icon + text: "Daily budget X% used — $Y.YY of $Z.ZZ limit"

### 8.4 Estimated Cost Over Time Chart

A line chart on the Costs page showing estimated cost per day for the last 30 days. Data is calculated by multiplying token counts from the requests table by the configured cost-per-token rates.

**Test after Phase 5:**
1. Navigate to the Costs page
2. Verify the cost table shows model entries
3. Click "Edit" on a cost entry — verify the edit modal appears
4. Change a cost value and save — verify the table updates
5. Click "Budget Limits" — verify the budget modal appears with daily/weekly/monthly inputs
6. Set a low daily budget (e.g., $0.01) — verify the Overview page shows a red warning banner
7. Verify the "Estimated Cost Over Time" chart renders with a line

---

## 9. Frontend Specification — Complete Visual and Functional Detail

This section defines every visual detail. Use the prototype JSX in Appendix A as the authoritative reference for layout and component structure, but translate it to vanilla HTML/CSS/JS.

### 9.1 Color System

All colors MUST use these exact hex values:

```css
:root {
    --bg:           #0a0e17;
    --surface:      #111827;
    --surface-alt:  #1a2332;
    --border:       #1e2d3d;
    --border-light: #2a3a4d;
    --text:         #e2e8f0;
    --text-muted:   #8899aa;
    --text-dim:     #556677;
    --accent:       #22d3ee;
    --accent-dim:   rgba(34, 211, 238, 0.12);
    --green:        #34d399;
    --green-dim:    rgba(52, 211, 153, 0.12);
    --yellow:       #fbbf24;
    --yellow-dim:   rgba(251, 191, 36, 0.12);
    --red:          #f87171;
    --red-dim:      rgba(248, 113, 113, 0.12);
    --purple:       #a78bfa;
    --purple-dim:   rgba(167, 139, 250, 0.12);
    --pink:         #f472b6;
    --orange:       #fb923c;
}
```

Service-specific colors:
```css
    --color-ollama:      #34d399;
    --color-openai:      #22d3ee;
    --color-anthropic:   #a78bfa;
    --color-elevenlabs:  #f472b6;
    --color-github:      #e2e8f0;
    --color-sora:        #fb923c;
    --color-kie:         #38bdf8;
    --color-openrouter:  #a78bfa;
    --color-getlate:     #fbbf24;
    --color-lmstudio:    #34d399;
    --color-google:      #34d399;
    --color-gitlab:      #fb923c;
    --color-custom:      #8899aa;
```

### 9.2 Typography

- **Primary font:** `'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif`
- **Monospace font:** `'JetBrains Mono', 'Fira Code', monospace`
- Both loaded from Google Fonts CDN

Usage rules:
- All body text, labels, buttons: DM Sans
- All numbers, values, code, URLs, model names, API keys: JetBrains Mono
- Stat card large numbers: JetBrains Mono, 28px, font-weight 700, letter-spacing -0.02em
- Section headings: DM Sans, 15px, font-weight 700
- Page titles: DM Sans, 22px, font-weight 700, letter-spacing -0.02em
- Labels/captions: DM Sans, 11-12px, font-weight 600, uppercase, letter-spacing 0.05em, color var(--text-dim)

### 9.3 Layout Structure

```
┌──────────────────────────────────────────────────────────┐
│  HEADER (sticky top, 65px height, glass effect)          │
│  [Logo] OpenClaw Hub     [N providers active] [Auth btn] │
├────────────┬─────────────────────────────────────────────┤
│  SIDEBAR   │  MAIN CONTENT AREA                          │
│  200px     │  padding: 28px                              │
│  fixed     │  scrollable                                 │
│            │                                             │
│  Overview  │  (varies by active view)                    │
│  Connect.  │                                             │
│  Costs     │                                             │
│  Activity  │                                             │
│            │                                             │
│  ───────   │                                             │
│  v1.0.0    │                                             │
│  Apache2.0 │                                             │
├────────────┴─────────────────────────────────────────────┤
│  MODAL OVERLAY (hidden by default, z-index 1000)         │
│  Semi-transparent black + backdrop blur                  │
└──────────────────────────────────────────────────────────┘
```

### 9.4 Component Specifications

#### Header
- Height: 65px (14px vertical padding)
- Background: `var(--surface)` at 80% opacity with `backdrop-filter: blur(12px)`
- Border bottom: `1px solid var(--border)`
- `position: sticky; top: 0; z-index: 100`
- Left: Shield icon (36x36px, gradient from accent to purple, 10px border-radius, glowing shadow) + "OpenClaw Hub" (16px bold) + "127.0.0.1:8080" (11px JetBrains Mono, dim)
- Right: Green dot + "{N} of {M} active" + Auth status button

#### Sidebar
- Width: 200px
- Background: `var(--surface)`
- Border right: `1px solid var(--border)`
- Nav buttons: 10px padding container, 4px gap between items
- Each nav button: `display: flex; align-items: center; gap: 10px; padding: 10px 14px; border-radius: 8px`
- Active state: background `var(--accent-dim)`, text color `var(--accent)`
- Hover state: background `var(--surface-alt)`
- Footer at bottom: version + license in dim text, separated by a top border

#### Card
- Background: `var(--surface)`
- Border: `1px solid var(--border)`
- Border-radius: 12px
- Padding: 24px

#### Stat Card
- Card layout with: icon in a 32x32 colored circle (8px border-radius) + uppercase label → large monospace number → optional subtitle in dim text
- Icon background uses the stat color at 15% opacity

#### Button Variants
- **Primary:** Background `var(--accent)`, color `var(--bg)`, 8px radius, bold
- **Ghost:** Transparent background, `1px solid var(--border)`, color `var(--text-muted)`
- **Danger:** Background `var(--red)`, color white
- **Size sm:** padding 6px 12px, font 12px
- **Size md:** padding 10px 18px, font 14px

#### Modal
- Overlay: `rgba(0,0,0,0.7)` with `backdrop-filter: blur(4px)`
- Container: `var(--surface)` background, `1px solid var(--border)`, 16px border-radius, 28px padding, max-width 90vw, max-height 85vh with overflow-y auto
- Header: title (18px bold) + X close button
- Click outside modal to close

#### Status Dot
- 8px circle with the status color
- `box-shadow: 0 0 8px {color}60` for glow effect
- For degraded/error: `animation: pulse 2s infinite` (0%/100% opacity 1, 50% opacity 0.4)
- Status text: 12px, bold, uppercase, matching color

#### Service Badge
- Inline badge showing the service category text
- 11px, font-weight 700, uppercase
- Color: service-specific color
- Background: service color at 10% opacity (`{color}18`)
- Padding: 2px 8px, border-radius: 4px

### 9.5 Charts Configuration

All charts use Chart.js 4.x with these shared options:

```javascript
const chartDefaults = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            labels: { color: '#8899aa', font: { size: 12 } }
        },
        tooltip: {
            backgroundColor: '#111827',
            borderColor: '#1e2d3d',
            borderWidth: 1,
            titleColor: '#e2e8f0',
            bodyColor: '#8899aa',
            cornerRadius: 8,
            titleFont: { weight: 'bold' }
        }
    },
    scales: {
        x: {
            ticks: { color: '#556677', font: { size: 11 } },
            grid: { color: '#1e2d3d', drawBorder: false },
            border: { color: '#1e2d3d' }
        },
        y: {
            ticks: { color: '#556677', font: { size: 11 } },
            grid: { color: '#1e2d3d', drawBorder: false },
            border: { display: false }
        }
    }
};
```

**Token Usage Chart (Overview page):**
- Type: Stacked Bar chart
- Datasets: one per provider (ollama=green, openai=cyan, anthropic=purple)
- Y-axis: Format large numbers as "45k" or "1.2M"
- Tab bar above chart for Day/Week/Month switching
- Destroy and recreate chart on period change

**Request Distribution Chart (Overview page):**
- Type: Doughnut chart (Pie with cutout)
- Inner radius: 50, outer radius: 75
- Segments: one per provider with service colors
- Legend below chart as inline colored squares + labels

**Estimated Cost Chart (Costs page):**
- Type: Line chart
- Single dataset in yellow (`var(--yellow)`)
- 2px line width, no dots
- Y-axis formatted as "$X.XX"

### 9.6 Animations

```css
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}
```

- Each view content area: `animation: fadeIn 0.3s ease-out` when displayed
- Status dots for non-healthy connections: `animation: pulse 2s infinite`

### 9.7 Scrollbar Styling

```css
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
```

### 9.8 Responsive Considerations

The dashboard is designed for desktop use (minimum 1024px width). However, the stat cards grid should collapse from 4 columns to 2 columns below 1200px:

```css
@media (max-width: 1200px) {
    .stat-grid { grid-template-columns: repeat(2, 1fr); }
}
```

No further mobile optimization is required for v1.

---

## 10. Service Template System — Complete Reference

The following table defines every service template. The JavaScript constant in `index.html` MUST match this exactly.

| Key | Name | Category | Icon | Color | baseUrl | apiKey | token | credPath | Default Base URL | Hint Text |
|-----|------|----------|------|-------|---------|--------|-------|----------|-----------------|-----------|
| `ollama` | Ollama (Local) | LLM (Local) | HardDrive | `#34d399` | ✅ | ❌ | ❌ | ❌ | `http://127.0.0.1:11434` | Local inference server — no authentication required |
| `openai` | OpenAI | LLM | Cloud | `#22d3ee` | ✅ | ✅ | ❌ | ❌ | `https://api.openai.com/v1` | Requires an API key from platform.openai.com |
| `anthropic` | Anthropic | LLM | Cloud | `#a78bfa` | ✅ | ✅ | ❌ | ❌ | `https://api.anthropic.com/v1` | Requires an API key from console.anthropic.com |
| `elevenlabs` | ElevenLabs | Media / Audio | Mic | `#f472b6` | ❌ | ✅ | ❌ | ❌ | `https://api.elevenlabs.io/v1` | Text-to-speech and voice cloning API |
| `sora` | Sora 2 (OpenAI) | Media / Video | Video | `#fb923c` | ❌ | ✅ | ❌ | ❌ | `https://api.openai.com/v1` | Uses your OpenAI API key — video generation endpoints |
| `kie` | Kie.ai | Media / Video | Video | `#38bdf8` | ❌ | ✅ | ❌ | ❌ | `https://api.kie.ai` | Cost-effective video generation — $0.24/5s |
| `github` | GitHub | Git / DevOps | GitBranch | `#e2e8f0` | ❌ | ❌ | ✅ | ❌ | `https://api.github.com` | Personal Access Token with repo + workflow scopes |
| `gitlab` | GitLab | Git / DevOps | GitBranch | `#fb923c` | ✅ | ❌ | ✅ | ❌ | `https://gitlab.com/api/v4` | PAT or project token — self-hosted instances need custom URL |
| `google` | Google (Drive/Sheets) | Data | FileText | `#34d399` | ❌ | ❌ | ❌ | ✅ | (empty) | Path to service account credentials JSON file |
| `openrouter` | OpenRouter | Gateway | Globe | `#a78bfa` | ✅ | ✅ | ❌ | ❌ | `https://openrouter.ai/api/v1` | Multi-model gateway — drop-in OpenAI compatible |
| `getlate` | getlate.dev | Gateway | Globe | `#fbbf24` | ✅ | ✅ | ❌ | ❌ | `https://api.getlate.dev/v1` | API gateway with rate limiting and caching |
| `lmstudio` | LM Studio | LLM (Local) | HardDrive | `#34d399` | ✅ | ❌ | ❌ | ❌ | `http://127.0.0.1:1234/v1` | Local model server — OpenAI-compatible API |
| `custom` | Custom Service | Custom | Settings | `#8899aa` | ✅ | ✅ | ✅ | ✅ | (empty) | Configure any service — enable only the fields you need |

**Category display order in the Add Connection picker:**
1. LLM
2. LLM (Local)
3. Media / Audio
4. Media / Video
5. Git / DevOps
6. Data
7. Gateway
8. Custom

**Icon mapping (use SVG icons or a lightweight icon set):**

Since we are NOT using lucide-react (that was only in the prototype), the implementing developer must either:
- Include inline SVGs for each icon (recommended — keeps it zero-dependency)
- Use a lightweight icon font/library loaded from CDN

Each icon should be 16px in the service picker cards and 20px in the connection list cards.

Recommended approach: Define simple SVG paths as JavaScript constants and inject them as `innerHTML`. This avoids any external icon dependency.

---

## 11. Security Considerations

### 11.1 Credential Encryption

All API keys and tokens stored in the `connections` table MUST be encrypted at rest using Fernet symmetric encryption from the `cryptography` Python library.

**Implementation:**
1. Add `cryptography>=42.0` to `requirements.txt`
2. On first run, check for `DASHBOARD_SECRET_KEY` in environment variables
3. If not found, generate one: `Fernet.generate_key().decode()`
4. Save it to `.env` as `DASHBOARD_SECRET_KEY=<generated_key>`
5. Print to console: `⚠️  Generated DASHBOARD_SECRET_KEY and saved to .env. Keep this secret safe.`
6. Use this key to encrypt/decrypt all credential values before database storage/retrieval

```python
from cryptography.fernet import Fernet

def encrypt_value(value: str, key: str) -> str:
    if not value:
        return ""
    f = Fernet(key.encode())
    return f.encrypt(value.encode()).decode()

def decrypt_value(encrypted: str, key: str) -> str:
    if not encrypted:
        return ""
    f = Fernet(key.encode())
    return f.decrypt(encrypted.encode()).decode()

def mask_value(value: str) -> str:
    if not value or len(value) < 8:
        return "****"
    return f"{value[:4]}...{value[-4:]}"
```

### 11.2 API Response Security

- The `GET /api/dashboard/connections` endpoint MUST NEVER return decrypted credentials. Only masked values.
- The full decrypted key is only used internally when Hub makes API calls to the provider.
- No endpoint should accept or return raw credentials in response bodies. Only the `POST` and `PUT` connection endpoints accept credentials in the request body, and they immediately encrypt before storage.

### 11.3 Localhost Binding

The dashboard MUST only be served on `127.0.0.1:8080`. The existing server configuration already binds to `127.0.0.1`. Do NOT change this to `0.0.0.0`.

### 11.4 Audit Logging

All connection CRUD operations should be logged to the existing audit log mechanism (if one exists) or to stdout with the format:
```
[DASHBOARD] Connection created: name="ElevenLabs", service="elevenlabs" (id=7)
[DASHBOARD] Connection updated: name="OpenAI" (id=2), fields=["name", "base_url"]
[DASHBOARD] Connection deleted: name="ElevenLabs" (id=7)
[DASHBOARD] API key updated for connection: name="OpenAI" (id=2)
```

Credentials values are NEVER logged.

### 11.5 Auth Gate (DEFERRED — Phase 2 Feature)

A local auth mechanism (PIN or token) for credential operations is deferred to a future PR. For v1, all dashboard endpoints are accessible without authentication since the server is localhost-only. This is documented as a known limitation.

---

## 12. Testing Checklist

Complete this checklist sequentially. Each test assumes all previous tests pass. Run the server with:
```bash
uvicorn aigateway.main:app --host 127.0.0.1 --port 8080 --reload
```

### 12.1 Database Tests

```bash
# After starting the server at least once:
sqlite3 aigateway.db ".tables"
# EXPECTED: Output includes 'connections', 'cost_configs', 'budget_limits' and the existing 'requests' table

sqlite3 aigateway.db ".schema connections"
# EXPECTED: Shows columns: id, name, service, category, base_url, api_key_encrypted, token_encrypted, cred_path, enabled, created_at, updated_at

sqlite3 aigateway.db ".schema cost_configs"
# EXPECTED: Shows columns: id, model, provider, input_cost_per_million, output_cost_per_million, updated_at

sqlite3 aigateway.db ".schema budget_limits"
# EXPECTED: Shows columns: id, daily_limit_usd, weekly_limit_usd, monthly_limit_usd, updated_at
```

### 12.2 API Endpoint Tests

```bash
# Stats
curl -s http://127.0.0.1:8080/api/dashboard/stats | python3 -m json.tool
# EXPECTED: JSON with keys: tokens_today, requests_24h, errors_24h, estimated_daily_cost_usd, active_connections, total_connections, budget

# Usage (daily)
curl -s "http://127.0.0.1:8080/api/dashboard/usage?period=daily" | python3 -m json.tool
# EXPECTED: JSON with keys: period, data (array)

# Usage (weekly)
curl -s "http://127.0.0.1:8080/api/dashboard/usage?period=weekly" | python3 -m json.tool
# EXPECTED: JSON with keys: period, data (array)

# Recent requests
curl -s "http://127.0.0.1:8080/api/dashboard/requests?limit=10" | python3 -m json.tool
# EXPECTED: JSON with key: requests (array of request objects)

# Connections (should be empty initially)
curl -s http://127.0.0.1:8080/api/dashboard/connections | python3 -m json.tool
# EXPECTED: JSON with key: connections (empty array or array of connection objects)

# Create a connection
curl -s -X POST http://127.0.0.1:8080/api/dashboard/connections \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Ollama","service":"ollama","category":"LLM (Local)","base_url":"http://127.0.0.1:11434","api_key":"","token":"","cred_path":""}' | python3 -m json.tool
# EXPECTED: JSON with id and message "Connection created..."

# List connections again
curl -s http://127.0.0.1:8080/api/dashboard/connections | python3 -m json.tool
# EXPECTED: Array with 1 connection, api_key_masked should be empty or "****"

# Toggle connection
curl -s -X PATCH http://127.0.0.1:8080/api/dashboard/connections/1/toggle | python3 -m json.tool
# EXPECTED: JSON with enabled: false

# Update connection
curl -s -X PUT http://127.0.0.1:8080/api/dashboard/connections/1 \
  -H "Content-Type: application/json" \
  -d '{"name":"Ollama Local Dev"}' | python3 -m json.tool
# EXPECTED: JSON with message "Connection updated..."

# Delete connection
curl -s -X DELETE http://127.0.0.1:8080/api/dashboard/connections/1 | python3 -m json.tool
# EXPECTED: JSON with message "Connection ... deleted"

# Budget
curl -s http://127.0.0.1:8080/api/dashboard/budget | python3 -m json.tool
# EXPECTED: JSON with daily_limit_usd, weekly_limit_usd, monthly_limit_usd

# Update budget
curl -s -X PUT http://127.0.0.1:8080/api/dashboard/budget \
  -H "Content-Type: application/json" \
  -d '{"daily_limit_usd":10.0,"weekly_limit_usd":50.0,"monthly_limit_usd":150.0}' | python3 -m json.tool
# EXPECTED: JSON with message "Budget limits updated"

# Costs
curl -s http://127.0.0.1:8080/api/dashboard/costs | python3 -m json.tool
# EXPECTED: JSON with key: costs (array)

# Create cost config
curl -s -X POST http://127.0.0.1:8080/api/dashboard/costs \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini","provider":"openai","input_cost_per_million":0.15,"output_cost_per_million":0.60}' | python3 -m json.tool
# EXPECTED: JSON with id and message
```

### 12.3 Existing Functionality Regression Tests

```bash
# Health endpoint still works
curl -s http://127.0.0.1:8080/health
# EXPECTED: Existing health response (must not be broken)

# Models endpoint still works
curl -s http://127.0.0.1:8080/v1/models | python3 -m json.tool
# EXPECTED: Existing models response

# Chat completions still work (if Ollama is running)
curl -s -X POST http://127.0.0.1:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5:32b-instruct","messages":[{"role":"user","content":"Say hi"}],"max_tokens":10}' | python3 -m json.tool
# EXPECTED: Chat completion response (if Ollama is running, otherwise a clear error)

# Swagger docs still accessible
# Navigate to http://127.0.0.1:8080/docs in a browser
# EXPECTED: Swagger UI loads with both existing endpoints AND new /api/dashboard/* endpoints
```

### 12.4 Browser UI Tests

Navigate to `http://127.0.0.1:8080/` and verify:

1. **Page loads:** Dashboard renders without console errors (check browser DevTools → Console)
2. **Header:** Shows "OpenClaw Hub", "127.0.0.1:8080", provider count, auth button
3. **Sidebar:** 4 navigation items — Overview, Connections, Costs, Activity. Version and license at bottom.
4. **Overview page:**
   - 4 stat cards in a row (Tokens Today, Requests 24h, Est. Daily Cost, Connections)
   - Token Usage bar chart renders (may be empty if no data)
   - Day/Week/Month tab bar switches the chart
   - Request Distribution pie chart renders
   - Connection Health section lists all connections with status dots
5. **Connections page:**
   - List of connection cards with name, service badge, status dot, base URL
   - Each card shows: Latency, Requests (24h), Errors (24h), and credential fields
   - "Add Connection" button opens the service picker modal
   - Service picker has search, categories in correct order, all 13 templates shown
   - Selecting a template advances to the configure step with correct fields
   - "← Back" returns to the picker
   - Submit creates the connection and it appears in the list
   - "Edit" opens the edit modal with correct fields for that service type
   - "Disable"/"Enable" toggles the card opacity
   - Trash icon shows inline delete confirmation
   - "Remove" deletes the connection
6. **Costs page:**
   - Budget progress bars (daily/weekly/monthly) with correct colors
   - Cost table with model, provider, input/output costs
   - Edit button opens cost edit modal
   - "Budget Limits" button opens budget edit modal
   - Estimated Cost chart renders
7. **Activity page:**
   - Table with columns: Time, Model, Service, Prompt, Completion, Cost, Latency, Status
   - Rows show correct data formatting (monospace numbers, "FREE" in green for $0, status badges)
   - Refresh button triggers a data reload

---

## 13. Documentation Updates

After implementation is complete, the following repository files MUST be updated:

### 13.1 README.md

Add a new section titled "## Dashboard" after the existing "## How It Works" section:

```markdown
## Dashboard

OpenClaw Hub includes a built-in web dashboard for monitoring and managing your connections.

**Access:** Navigate to `http://127.0.0.1:8080/` after starting the server.

**Features:**
- Real-time overview of token usage, request counts, and estimated costs
- Visual charts for usage trends (daily, weekly, monthly)
- Connection management — add, edit, disable, or remove service connections
- Support for diverse service types: LLM providers, media APIs, Git platforms, gateways, and custom services
- Per-model cost-per-token configuration
- Budget alerts with daily, weekly, and monthly limits

**Screenshot:**
(Add a screenshot of the Overview page here)
```

### 13.2 CHANGELOG.md

Add entry:

```markdown
## [1.1.0] - YYYY-MM-DD

### Added
- Web dashboard accessible at http://127.0.0.1:8080/
- Dashboard API endpoints under /api/dashboard/*
- Connection management with template-driven Add flow supporting 12 service types
- Token usage charts (daily/weekly/monthly) with per-provider breakdown
- Cost-per-token configuration with per-model granularity
- Budget limits (daily/weekly/monthly) with threshold alerts
- Recent request activity feed
- Connection health monitoring
- Encrypted credential storage for API keys and tokens
```

### 13.3 STATUS.md

Update the status to reflect the dashboard feature.

### 13.4 .env.example

Add:
```
# Dashboard credential encryption key (auto-generated on first run if not set)
# DASHBOARD_SECRET_KEY=
```

### 13.5 requirements.txt

Add (if not already present):
```
cryptography>=42.0
aiofiles>=23.0
```

---

## 14. Future Work (Out of Scope)

The following features are explicitly NOT part of this implementation. They are noted here for future PRs:

1. **Auth gate** — PIN/token authentication for credential management operations
2. **Connection validation on Add** — Actually testing the connection before saving (v1 saves without validation)
3. **Auto-discovery of models** — Querying providers to populate the cost config table automatically
4. **Export/import** — Exporting dashboard config and connections for backup/migration
5. **Real-time updates** — WebSocket-based live updating of stats and activity feed
6. **Provider-specific health checks** — Tailored health check logic per service type (e.g., list models for LLMs, ping for media APIs)
7. **Mobile-responsive layout** — Full responsive design for phone/tablet access
8. **Dark/light theme toggle** — Currently dark theme only

---

## 15. Appendix A: UI Prototype Reference (JSX)

The file `openclaw-hub-dashboard.jsx` is a React prototype that demonstrates the exact layout, interactions, colors, and component structure of the dashboard. It was built as a design reference and is NOT intended to be used directly in the implementation.

**How to use this reference:**
- Copy color values, spacing, font sizes, and layout patterns
- Study the component structure to understand the HTML hierarchy
- Use the service template constant (`SERVICE_TEMPLATES`) as the definitive list
- Translate React state management to vanilla JS DOM manipulation
- Translate React event handlers to `addEventListener` calls

**The prototype file should be saved in the repo at:**
```
docs/dashboard-prototype.jsx
```

This serves as design documentation for future contributors.

**IMPORTANT:** The implementing developer should have access to the prototype file. If working in an environment where the JSX can be rendered (e.g., a React sandbox), viewing it first will dramatically reduce ambiguity in implementation. The rendered prototype IS the specification — every visual detail in the prototype is intentional and should be replicated.

---

*End of specification. All questions about implementation details should be resolved by referencing the relevant section of this document or the prototype JSX in Appendix A.*
