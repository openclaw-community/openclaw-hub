"""
Dashboard API endpoints — stats, connections, costs, budget, health.
"""

import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy import case as sa_case
from sqlalchemy.ext.asyncio import AsyncSession

from aigateway.dashboard import data
from aigateway.dashboard.crypto import get_or_create_secret_key, encrypt_value
from aigateway.storage.database import get_session
from aigateway.storage.models import BudgetLimit, Connection, CostConfig, Request, ApiCall

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


# ---------------------------------------------------------------------------
# .env utility functions
# ---------------------------------------------------------------------------

def _find_env_path() -> str:
    """Find the .env file relative to the project root."""
    import os
    # aigateway/api/dashboard.py → go up 2 levels to project root
    base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base, ".env")


def _write_env_key(key: str, value: str) -> None:
    """Write or update a key in the .env file. Safe: replaces in-place if exists, appends if not."""
    env_path = _find_env_path()
    try:
        with open(env_path, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        content = ""

    pattern = rf'^{re.escape(key)}=.*$'
    replacement = f'{key}={value}'

    if re.search(pattern, content, flags=re.MULTILINE):
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    else:
        if content and not content.endswith('\n'):
            content += '\n'
        content += f'{replacement}\n'

    with open(env_path, 'w') as f:
        f.write(content)
    print(f'[DASHBOARD] .env updated: {key}=***')


def _remove_env_key(key: str) -> None:
    """Comment out a key in the .env file (prefix with #)."""
    env_path = _find_env_path()
    try:
        with open(env_path, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        return

    pattern = rf'^({re.escape(key)}=.*)$'
    content = re.sub(pattern, r'# \1', content, flags=re.MULTILINE)

    with open(env_path, 'w') as f:
        f.write(content)
    print(f'[DASHBOARD] .env key commented out: {key}')


# ---------------------------------------------------------------------------
# Import from .env — provider map
# ---------------------------------------------------------------------------

ENV_IMPORT_MAP = [
    {
        "env_key": "OPENAI_API_KEY",
        "service": "openai",
        "name": "OpenAI",
        "category": "LLM",
        "credential_field": "api_key",
        "base_url": "https://api.openai.com/v1",
    },
    {
        "env_key": "ANTHROPIC_API_KEY",
        "service": "anthropic",
        "name": "Anthropic",
        "category": "LLM",
        "credential_field": "api_key",
        "base_url": "https://api.anthropic.com/v1",
    },
    {
        "env_key": "OLLAMA_URL",
        "service": "ollama",
        "name": "Ollama (Local)",
        "category": "LLM (Local)",
        "credential_field": "base_url",  # base_url, not api_key
        "base_url": None,  # value comes from env
    },
    {
        "env_key": "GITHUB_TOKEN",
        "service": "github",
        "name": "GitHub",
        "category": "Git / DevOps",
        "credential_field": "token",
        "base_url": "https://api.github.com",
    },
    {
        "env_key": "LATE_API_KEY",
        "service": "getlate",
        "name": "getlate.dev",
        "category": "Gateway",
        "credential_field": "api_key",
        "base_url": "https://api.getlate.dev/v1",
    },
    {
        "env_key": "ELEVENLABS_API_KEY",
        "service": "elevenlabs",
        "name": "ElevenLabs",
        "category": "Media / Audio",
        "credential_field": "api_key",
        "base_url": "https://api.elevenlabs.io/v1",
    },
    {
        "env_key": "KIE_API_KEY",
        "service": "kie",
        "name": "Kie.ai",
        "category": "Media / Video",
        "credential_field": "api_key",
        "base_url": "https://api.kie.ai",
    },
]


# Service classification
LLM_SERVICES = {'openai', 'anthropic', 'ollama', 'openrouter', 'getlate', 'lmstudio', 'custom'}

ENV_KEY_MAP = {
    'openai':     {'api_key': 'OPENAI_API_KEY'},
    'anthropic':  {'api_key': 'ANTHROPIC_API_KEY'},
    'ollama':     {'base_url': 'OLLAMA_URL'},
    'openrouter': {'api_key': 'OPENROUTER_API_KEY'},
    'getlate':    {'api_key': 'GETLATE_API_KEY'},
    'lmstudio':   {'base_url': 'LMSTUDIO_URL'},
    'custom':     {'api_key': 'CUSTOM_API_KEY', 'base_url': 'CUSTOM_BASE_URL'},
}


def _sync_env_for_connection(service: str, api_key_plain: str = "", token_plain: str = "", base_url: str = "") -> bool:
    """Write relevant .env keys for an LLM service. Returns True if restart is needed."""
    if service not in LLM_SERVICES:
        return False

    mapping = ENV_KEY_MAP.get(service, {})
    if 'api_key' in mapping and api_key_plain:
        _write_env_key(mapping['api_key'], api_key_plain)
    if 'base_url' in mapping and base_url:
        _write_env_key(mapping['base_url'], base_url)

    return True


def _remove_env_for_connection(service: str) -> bool:
    """Comment out .env keys for a deleted LLM connection. Returns True if restart needed."""
    if service not in LLM_SERVICES:
        return False
    mapping = ENV_KEY_MAP.get(service, {})
    for _, env_key in mapping.items():
        _remove_env_key(env_key)
    return True


# ---------------------------------------------------------------------------
# Stats & Usage
# ---------------------------------------------------------------------------

@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_session)):
    """Aggregated 24-hour stats plus budget snapshot."""
    stats_24h = await data.get_request_stats_24h(db)
    api_calls_24h = await data.get_api_call_count_24h(db)
    daily_cost = await data.get_estimated_costs(db, "daily")
    weekly_cost = await data.get_estimated_costs(db, "weekly")
    monthly_cost = await data.get_estimated_costs(db, "monthly")
    budget = await data.get_budget_limits(db)

    # Count connections
    conn_result = await db.execute(select(func.count(Connection.id)))
    total_connections = conn_result.scalar() or 0
    active_result = await db.execute(
        select(func.count(Connection.id)).where(Connection.enabled == True)
    )
    active_connections = active_result.scalar() or 0

    daily_limit = budget["daily_limit_usd"]
    weekly_limit = budget["weekly_limit_usd"]
    monthly_limit = budget["monthly_limit_usd"]
    daily_spent = daily_cost["estimated_cost_usd"]
    weekly_spent = weekly_cost["estimated_cost_usd"]
    monthly_spent = monthly_cost["estimated_cost_usd"]

    llm_requests_24h = stats_24h["total_requests"]
    total_requests_24h = llm_requests_24h + api_calls_24h

    return {
        "tokens_today": stats_24h["total_prompt_tokens"] + stats_24h["total_completion_tokens"],
        "requests_24h": total_requests_24h,       # LLM + non-LLM combined
        "llm_requests_24h": llm_requests_24h,     # LLM completions only
        "api_calls_24h": api_calls_24h,           # non-LLM API calls only
        "errors_24h": stats_24h["total_errors"],
        "estimated_daily_cost_usd": daily_spent,
        "active_connections": active_connections,
        "total_connections": total_connections,
        "budget": {
            "daily_limit": daily_limit,
            "daily_spent": daily_spent,
            "daily_pct": round((daily_spent / daily_limit * 100) if daily_limit > 0 else 0, 1),
            "weekly_limit": weekly_limit,
            "weekly_spent": weekly_spent,
            "weekly_pct": round((weekly_spent / weekly_limit * 100) if weekly_limit > 0 else 0, 1),
            "monthly_limit": monthly_limit,
            "monthly_spent": monthly_spent,
            "monthly_pct": round((monthly_spent / monthly_limit * 100) if monthly_limit > 0 else 0, 1),
        },
    }


@router.get("/usage")
async def get_usage(
    period: str = Query("daily", pattern="^(daily|weekly|monthly)$"),
    db: AsyncSession = Depends(get_session),
):
    """
    Token usage and request counts pivoted by date/week/month.

    Returns:
    - data[].by_provider: token counts per LLM provider (for token chart)
    - data[].requests_by_service: request counts per service (LLM + non-LLM combined)
    """
    if period == "daily":
        raw_tokens = await data.get_token_usage_daily(db)
        raw_api = await data.get_api_calls_by_service_daily(db)
        date_key = "date"
    elif period == "weekly":
        raw_tokens = await data.get_token_usage_weekly(db)
        raw_api = await data.get_api_calls_by_service_weekly(db)
        date_key = "week"
    else:
        raw_tokens = await data.get_token_usage_monthly(db)
        raw_api = await data.get_api_calls_by_service_monthly(db)
        date_key = "month"

    # Build token chart data (existing behaviour)
    grouped: dict = defaultdict(lambda: {"by_provider": {}, "total": 0, "requests_by_service": {}})
    for row in raw_tokens:
        key = row[date_key]
        provider = row["provider"]
        tokens = row["total_tokens"]
        grouped[key]["by_provider"][provider] = tokens
        grouped[key]["total"] += tokens
        # Also count LLM completions as requests per provider
        grouped[key]["requests_by_service"][provider] = (
            grouped[key]["requests_by_service"].get(provider, 0) + 1
        )

    # Merge non-LLM API call counts into requests_by_service
    for row in raw_api:
        key = row[date_key]
        service = row["service"]
        count = row["total_requests"]
        if key not in grouped:
            grouped[key] = {"by_provider": {}, "total": 0, "requests_by_service": {}}
        grouped[key]["requests_by_service"][service] = (
            grouped[key]["requests_by_service"].get(service, 0) + count
        )

    data_out = [
        {
            date_key: k,
            "by_provider": v["by_provider"],
            "total": v["total"],
            "requests_by_service": v["requests_by_service"],
        }
        for k, v in sorted(grouped.items())
    ]
    return {"period": period, "data": data_out}


@router.get("/requests")
async def get_requests(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_session),
):
    """Recent LLM completion requests ordered by timestamp DESC."""
    requests = await data.get_recent_requests(db, limit=limit)
    return {"requests": requests}


@router.get("/api-calls")
async def get_api_calls(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_session),
):
    """Recent non-LLM API calls (GitHub, social, etc.) ordered by timestamp DESC."""
    calls = await data.get_recent_api_calls(db, limit=limit)
    return {"api_calls": calls}


# ---------------------------------------------------------------------------
# Connections CRUD
# ---------------------------------------------------------------------------

class ConnectionCreate(BaseModel):
    name: str
    service: str
    category: str
    base_url: str = ""
    api_key: str = ""
    token: str = ""
    cred_path: str = ""


class ConnectionUpdate(BaseModel):
    name: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None   # empty string = keep existing
    token: Optional[str] = None     # empty string = keep existing
    cred_path: Optional[str] = None


@router.get("/connections")
async def get_connections(db: AsyncSession = Depends(get_session)):
    """All connections with masked credentials."""
    connections = await data.get_connections(db)
    return {"connections": connections}


@router.post("/connections", status_code=201)
async def create_connection(body: ConnectionCreate, db: AsyncSession = Depends(get_session)):
    """Create a new connection (credentials are encrypted at rest)."""
    key = get_or_create_secret_key()
    conn = Connection(
        name=body.name,
        service=body.service,
        category=body.category,
        base_url=body.base_url,
        api_key_encrypted=encrypt_value(body.api_key, key) if body.api_key else "",
        token_encrypted=encrypt_value(body.token, key) if body.token else "",
        cred_path=body.cred_path,
        enabled=True,
    )
    db.add(conn)
    await db.commit()
    await db.refresh(conn)

    # Sync to .env for LLM providers
    restart_required = _sync_env_for_connection(
        service=body.service,
        api_key_plain=body.api_key,
        token_plain=body.token,
        base_url=body.base_url,
    )

    print(f'[DASHBOARD] Connection created: name="{conn.name}", service="{conn.service}" (id={conn.id})')

    msg = "Connection created successfully"
    if restart_required:
        msg = "Connection saved. Restart Hub for routing changes to take effect."

    return {
        "id": conn.id,
        "name": conn.name,
        "service": conn.service,
        "message": msg,
        "restart_required": restart_required,
    }


@router.put("/connections/{conn_id}")
async def update_connection(
    conn_id: int, body: ConnectionUpdate, db: AsyncSession = Depends(get_session)
):
    """Update an existing connection. Credentials are only updated when non-empty."""
    result = await db.execute(select(Connection).where(Connection.id == conn_id))
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail=f"Connection {conn_id} not found")

    updated_fields = []
    fernet_key = get_or_create_secret_key()
    new_api_key_plain = ""
    new_base_url = ""

    if body.name is not None:
        conn.name = body.name
        updated_fields.append("name")
    if body.base_url is not None:
        conn.base_url = body.base_url
        new_base_url = body.base_url
        updated_fields.append("base_url")
    if body.api_key:  # Only update if non-empty
        conn.api_key_encrypted = encrypt_value(body.api_key, fernet_key)
        new_api_key_plain = body.api_key
        updated_fields.append("api_key")
        print(f'[DASHBOARD] API key updated for connection: name="{conn.name}" (id={conn_id})')
    if body.token:  # Only update if non-empty
        conn.token_encrypted = encrypt_value(body.token, fernet_key)
        updated_fields.append("token")
    if body.cred_path is not None:
        conn.cred_path = body.cred_path
        updated_fields.append("cred_path")

    await db.commit()

    # Sync .env if credentials or base_url changed for LLM services
    restart_required = False
    if new_api_key_plain or new_base_url:
        restart_required = _sync_env_for_connection(
            service=conn.service,
            api_key_plain=new_api_key_plain,
            base_url=new_base_url,
        )

    print(f'[DASHBOARD] Connection updated: name="{conn.name}" (id={conn_id}), fields={updated_fields}')

    msg = "Connection updated successfully"
    if restart_required:
        msg = "Connection saved. Restart Hub for routing changes to take effect."

    return {"id": conn.id, "name": conn.name, "message": msg, "restart_required": restart_required}


@router.delete("/connections/{conn_id}")
async def delete_connection(conn_id: int, db: AsyncSession = Depends(get_session)):
    """Delete a connection by ID."""
    result = await db.execute(select(Connection).where(Connection.id == conn_id))
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail=f"Connection {conn_id} not found")
    name = conn.name
    service = conn.service
    await db.delete(conn)
    await db.commit()

    restart_required = _remove_env_for_connection(service)
    print(f'[DASHBOARD] Connection deleted: name="{name}" (id={conn_id})')

    msg = f"Connection '{name}' deleted"
    if restart_required:
        msg += ". Restart Hub for routing changes to take effect."

    return {"message": msg, "restart_required": restart_required}


@router.patch("/connections/{conn_id}/toggle")
async def toggle_connection(conn_id: int, db: AsyncSession = Depends(get_session)):
    """Toggle the enabled state of a connection."""
    result = await db.execute(select(Connection).where(Connection.id == conn_id))
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail=f"Connection {conn_id} not found")
    conn.enabled = not conn.enabled
    await db.commit()
    state = "enabled" if conn.enabled else "disabled"
    return {"id": conn.id, "enabled": conn.enabled, "message": f"Connection '{conn.name}' {state}"}


@router.post("/connections/import-env", status_code=200)
async def import_connections_from_env(db: AsyncSession = Depends(get_session)):
    """
    Scan environment variables for configured providers.
    For each detected provider that doesn't already have a matching connection,
    create a connection entry. Idempotent — safe to call repeatedly.
    """
    import os

    # Get existing connections to check for duplicates (match on service type)
    existing_result = await db.execute(select(Connection))
    existing = existing_result.scalars().all()
    existing_services = {c.service for c in existing}

    fernet_key = get_or_create_secret_key()
    imported = []
    skipped = []

    # Always try to import Ollama (it's local, no API key required)
    ollama_url = os.environ.get("OLLAMA_URL") or "http://127.0.0.1:11434"

    for mapping in ENV_IMPORT_MAP:
        service = mapping["service"]
        env_key = mapping["env_key"]

        # Special case: Ollama is always available, use default if env var missing
        if service == "ollama":
            raw_value = ollama_url
        else:
            raw_value = os.environ.get(env_key, "")

        if not raw_value:
            # Env var not set — skip
            continue

        if service in existing_services:
            skipped.append(mapping["name"])
            continue

        # Determine field values
        api_key_plain = ""
        token_plain = ""
        base_url = mapping["base_url"] or ""

        if mapping["credential_field"] == "api_key":
            api_key_plain = raw_value
        elif mapping["credential_field"] == "token":
            token_plain = raw_value
        elif mapping["credential_field"] == "base_url":
            base_url = raw_value

        conn = Connection(
            name=mapping["name"],
            service=service,
            category=mapping["category"],
            base_url=base_url,
            api_key_encrypted=encrypt_value(api_key_plain, fernet_key) if api_key_plain else "",
            token_encrypted=encrypt_value(token_plain, fernet_key) if token_plain else "",
            cred_path="",
            enabled=True,
        )
        db.add(conn)
        imported.append(mapping["name"])
        print(f'[DASHBOARD] Imported connection from .env: name="{mapping["name"]}", service="{service}"')

    if imported:
        await db.commit()

    count_i = len(imported)
    count_s = len(skipped)
    parts = []
    if count_i:
        parts.append(f"Imported {count_i} connection{'s' if count_i != 1 else ''}")
    if count_s:
        parts.append(f"skipped {count_s} already registered")
    if not parts:
        parts.append("Nothing to import — all providers already registered or no env vars found")

    return {
        "imported": imported,
        "skipped": skipped,
        "message": ", ".join(parts),
    }


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@router.get("/health")
async def get_health(db: AsyncSession = Depends(get_session)):
    """Per-connection health based on last hour of request data."""
    result = await db.execute(select(Connection).where(Connection.enabled == True))
    connections = result.scalars().all()

    since = datetime.now(timezone.utc) - timedelta(hours=1)
    statuses = []

    for conn in connections:
        req_result = await db.execute(
            select(
                func.count(Request.id).label("total"),
                func.sum(sa_case((Request.success == False, 1), else_=0)).label("errors"),
                func.avg(Request.latency_ms).label("avg_latency"),
            )
            .where(Request.provider == conn.service)
            .where(Request.timestamp >= since)
        )
        row = req_result.one()
        avg_latency = row.avg_latency or 0
        errors = row.errors or 0
        total = row.total or 0
        error_rate = (errors / total) if total > 0 else 0

        status = "degraded" if (error_rate > 0.05 or avg_latency >= 2000) else "healthy"
        statuses.append({
            "id": conn.id,
            "name": conn.name,
            "status": status,
            "latency_ms": round(avg_latency, 1),
        })

    return {"connections": statuses}


# ---------------------------------------------------------------------------
# Costs CRUD
# ---------------------------------------------------------------------------

class CostConfigCreate(BaseModel):
    model: str
    provider: str
    input_cost_per_million: float = 0.0
    output_cost_per_million: float = 0.0


class CostConfigUpdate(BaseModel):
    input_cost_per_million: float
    output_cost_per_million: float


@router.get("/costs")
async def get_costs(db: AsyncSession = Depends(get_session)):
    """All cost configurations."""
    costs = await data.get_cost_configs(db)
    return {"costs": costs}


@router.post("/costs", status_code=201)
async def create_cost_config(body: CostConfigCreate, db: AsyncSession = Depends(get_session)):
    """Create a cost configuration for a model."""
    config = CostConfig(
        model=body.model,
        provider=body.provider,
        input_cost_per_million=body.input_cost_per_million,
        output_cost_per_million=body.output_cost_per_million,
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return {"id": config.id, "message": "Cost config created"}


@router.put("/costs/{config_id}")
async def update_cost_config(
    config_id: int, body: CostConfigUpdate, db: AsyncSession = Depends(get_session)
):
    """Update input/output cost rates for an existing cost config."""
    result = await db.execute(select(CostConfig).where(CostConfig.id == config_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail=f"Cost config {config_id} not found")
    config.input_cost_per_million = body.input_cost_per_million
    config.output_cost_per_million = body.output_cost_per_million
    await db.commit()
    return {"id": config.id, "message": "Cost config updated"}


@router.delete("/costs/{config_id}")
async def delete_cost_config(config_id: int, db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(CostConfig).where(CostConfig.id == config_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail=f"Cost config {config_id} not found")
    model_name = config.model
    await db.delete(config)
    await db.commit()
    return {"message": f"Cost config for '{model_name}' deleted"}


# ---------------------------------------------------------------------------
# Budget
# ---------------------------------------------------------------------------

class BudgetUpdate(BaseModel):
    daily_limit_usd: float
    weekly_limit_usd: float
    monthly_limit_usd: float


@router.get("/budget")
async def get_budget(db: AsyncSession = Depends(get_session)):
    """Current budget limits."""
    limits = await data.get_budget_limits(db)
    return {
        "daily_limit_usd": limits["daily_limit_usd"],
        "weekly_limit_usd": limits["weekly_limit_usd"],
        "monthly_limit_usd": limits["monthly_limit_usd"],
    }


@router.put("/budget")
async def update_budget(body: BudgetUpdate, db: AsyncSession = Depends(get_session)):
    """Update budget limits (upsert — creates default row if none exists)."""
    result = await db.execute(select(BudgetLimit).limit(1))
    limit_row = result.scalar_one_or_none()
    if limit_row is None:
        limit_row = BudgetLimit()
        db.add(limit_row)
    limit_row.daily_limit_usd = body.daily_limit_usd
    limit_row.weekly_limit_usd = body.weekly_limit_usd
    limit_row.monthly_limit_usd = body.monthly_limit_usd
    await db.commit()
    return {"message": "Budget limits updated"}
