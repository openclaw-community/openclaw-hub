"""
Dashboard API endpoints — stats, connections, costs, budget, health.
"""

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
from aigateway.storage.models import BudgetLimit, Connection, CostConfig, Request

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


# ---------------------------------------------------------------------------
# Stats & Usage
# ---------------------------------------------------------------------------

@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_session)):
    """Aggregated 24-hour stats plus budget snapshot."""
    stats_24h = await data.get_request_stats_24h(db)
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

    return {
        "tokens_today": stats_24h["total_prompt_tokens"] + stats_24h["total_completion_tokens"],
        "requests_24h": stats_24h["total_requests"],
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
    """Token usage pivoted by date/week/month and provider."""
    if period == "daily":
        raw = await data.get_token_usage_daily(db)
        date_key = "date"
    elif period == "weekly":
        raw = await data.get_token_usage_weekly(db)
        date_key = "week"
    else:
        raw = await data.get_token_usage_monthly(db)
        date_key = "month"

    grouped: dict = defaultdict(lambda: {"by_provider": {}, "total": 0})
    for row in raw:
        key = row[date_key]
        provider = row["provider"]
        tokens = row["total_tokens"]
        grouped[key]["by_provider"][provider] = tokens
        grouped[key]["total"] += tokens

    data_out = [
        {date_key: k, "by_provider": v["by_provider"], "total": v["total"]}
        for k, v in sorted(grouped.items())
    ]
    return {"period": period, "data": data_out}


@router.get("/requests")
async def get_requests(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_session),
):
    """Recent requests ordered by timestamp DESC."""
    requests = await data.get_recent_requests(db, limit=limit)
    return {"requests": requests}


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
    print(f'[DASHBOARD] Connection created: name="{conn.name}", service="{conn.service}" (id={conn.id})')
    return {
        "id": conn.id,
        "name": conn.name,
        "service": conn.service,
        "message": "Connection created successfully",
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
    key = get_or_create_secret_key()

    if body.name is not None:
        conn.name = body.name
        updated_fields.append("name")
    if body.base_url is not None:
        conn.base_url = body.base_url
        updated_fields.append("base_url")
    if body.api_key:  # Only update if non-empty
        conn.api_key_encrypted = encrypt_value(body.api_key, key)
        updated_fields.append("api_key")
        print(f'[DASHBOARD] API key updated for connection: name="{conn.name}" (id={conn_id})')
    if body.token:  # Only update if non-empty
        conn.token_encrypted = encrypt_value(body.token, key)
        updated_fields.append("token")
    if body.cred_path is not None:
        conn.cred_path = body.cred_path
        updated_fields.append("cred_path")

    await db.commit()
    print(f'[DASHBOARD] Connection updated: name="{conn.name}" (id={conn_id}), fields={updated_fields}')
    return {"id": conn.id, "name": conn.name, "message": "Connection updated successfully"}


@router.delete("/connections/{conn_id}")
async def delete_connection(conn_id: int, db: AsyncSession = Depends(get_session)):
    """Delete a connection by ID."""
    result = await db.execute(select(Connection).where(Connection.id == conn_id))
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail=f"Connection {conn_id} not found")
    name = conn.name
    await db.delete(conn)
    await db.commit()
    print(f'[DASHBOARD] Connection deleted: name="{name}" (id={conn_id})')
    return {"message": f"Connection '{name}' deleted"}


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
