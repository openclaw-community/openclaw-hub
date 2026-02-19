"""
Data access layer for dashboard queries.
All functions are async — they use AsyncSession.
"""

from datetime import datetime, timedelta, timezone
from sqlalchemy import func, select, desc, text, case
from sqlalchemy.ext.asyncio import AsyncSession
from aigateway.storage.models import Request, Connection, CostConfig, BudgetLimit
from aigateway.dashboard.crypto import get_or_create_secret_key, mask_value, decrypt_value


def _derive_status(success: bool, error) -> str:
    """Convert Boolean success + error text to a status string."""
    return "success" if success else "error"


async def get_token_usage_daily(db: AsyncSession, days: int = 30) -> list:
    """Token usage aggregated by day and provider for the last N days."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(
            func.date(Request.timestamp).label("date"),
            Request.provider,
            func.sum(Request.total_tokens).label("total_tokens")
        )
        .where(Request.timestamp >= since)
        .group_by(func.date(Request.timestamp), Request.provider)
        .order_by(func.date(Request.timestamp).asc())
    )
    rows = result.all()
    return [{"date": str(r.date), "provider": r.provider or "unknown", "total_tokens": r.total_tokens or 0} for r in rows]


async def get_token_usage_weekly(db: AsyncSession, weeks: int = 12) -> list:
    """Token usage aggregated by ISO week and provider for the last N weeks."""
    since = datetime.now(timezone.utc) - timedelta(weeks=weeks)
    result = await db.execute(
        select(
            func.strftime('%Y-W%W', Request.timestamp).label("week"),
            Request.provider,
            func.sum(Request.total_tokens).label("total_tokens")
        )
        .where(Request.timestamp >= since)
        .group_by(func.strftime('%Y-W%W', Request.timestamp), Request.provider)
        .order_by(func.strftime('%Y-W%W', Request.timestamp).asc())
    )
    rows = result.all()
    return [{"week": r.week, "provider": r.provider or "unknown", "total_tokens": r.total_tokens or 0} for r in rows]


async def get_token_usage_monthly(db: AsyncSession, months: int = 6) -> list:
    """Token usage aggregated by month and provider for the last N months."""
    since = datetime.now(timezone.utc) - timedelta(days=months * 30)
    result = await db.execute(
        select(
            func.strftime('%Y-%m', Request.timestamp).label("month"),
            Request.provider,
            func.sum(Request.total_tokens).label("total_tokens")
        )
        .where(Request.timestamp >= since)
        .group_by(func.strftime('%Y-%m', Request.timestamp), Request.provider)
        .order_by(func.strftime('%Y-%m', Request.timestamp).asc())
    )
    rows = result.all()
    return [{"month": r.month, "provider": r.provider or "unknown", "total_tokens": r.total_tokens or 0} for r in rows]


async def get_request_stats_24h(db: AsyncSession) -> dict:
    """Aggregate stats for the last 24 hours."""
    since = datetime.now(timezone.utc) - timedelta(hours=24)

    result = await db.execute(
        select(
            Request.provider,
            func.count(Request.id).label("requests"),
            func.sum(case((Request.success == False, 1), else_=0)).label("errors"),
            func.sum(Request.total_tokens).label("tokens"),
            func.sum(Request.cost_usd).label("cost_usd")
        )
        .where(Request.timestamp >= since)
        .group_by(Request.provider)
    )
    rows = result.all()

    by_provider = {}
    total_requests = 0
    total_errors = 0
    total_tokens = 0
    total_cost = 0.0

    for r in rows:
        provider = r.provider or "unknown"
        by_provider[provider] = {
            "requests": r.requests or 0,
            "errors": r.errors or 0,
            "tokens": r.tokens or 0,
            "cost_usd": round(r.cost_usd or 0.0, 6)
        }
        total_requests += r.requests or 0
        total_errors += r.errors or 0
        total_tokens += r.tokens or 0
        total_cost += r.cost_usd or 0.0

    # Get prompt/completion split separately
    token_result = await db.execute(
        select(
            func.sum(Request.prompt_tokens).label("prompt"),
            func.sum(Request.completion_tokens).label("completion")
        ).where(Request.timestamp >= since)
    )
    token_row = token_result.one()

    return {
        "total_requests": total_requests,
        "total_errors": total_errors,
        "total_prompt_tokens": token_row.prompt or 0,
        "total_completion_tokens": token_row.completion or 0,
        "total_cost_usd": round(total_cost, 6),
        "by_provider": by_provider
    }


async def get_recent_requests(db: AsyncSession, limit: int = 50) -> list:
    """Most recent N requests ordered by timestamp DESC."""
    result = await db.execute(
        select(Request)
        .order_by(desc(Request.timestamp))
        .limit(min(limit, 200))
    )
    rows = result.scalars().all()
    return [{
        "id": str(r.id),
        "created_at": r.timestamp.isoformat() + "Z" if r.timestamp else None,
        "model": r.model,
        "provider": r.provider or "unknown",
        "prompt_tokens": r.prompt_tokens or 0,
        "completion_tokens": r.completion_tokens or 0,
        "cost_usd": round(r.cost_usd or 0.0, 6),
        "latency_ms": r.latency_ms or 0,
        "status": _derive_status(r.success, r.error)
    } for r in rows]


async def get_connections(db: AsyncSession) -> list:
    """All connections with masked credentials and computed health stats."""
    result = await db.execute(select(Connection).order_by(Connection.id))
    connections = result.scalars().all()

    since_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    output = []

    for conn in connections:
        # Get stats from requests table using provider name matching the connection's service
        req_result = await db.execute(
            select(
                func.count(Request.id).label("total"),
                func.sum(case((Request.success == False, 1), else_=0)).label("errors"),
                func.avg(Request.latency_ms).label("avg_latency")
            )
            .where(Request.provider == conn.service)
            .where(Request.timestamp >= since_24h)
        )
        req_row = req_result.one()

        # Compute health status
        avg_latency = req_row.avg_latency or 0
        error_count = req_row.errors or 0
        total = req_row.total or 0
        error_rate = (error_count / total) if total > 0 else 0

        if not conn.enabled:
            status = "offline"
        elif error_rate > 0.05 or avg_latency >= 2000:
            status = "degraded"
        else:
            status = "healthy"

        # Mask credentials
        key = get_or_create_secret_key()
        api_key_masked = ""
        token_masked = ""
        if conn.api_key_encrypted:
            try:
                decrypted = decrypt_value(conn.api_key_encrypted, key)
                api_key_masked = mask_value(decrypted)
            except Exception:
                api_key_masked = "****"
        if conn.token_encrypted:
            try:
                decrypted = decrypt_value(conn.token_encrypted, key)
                token_masked = mask_value(decrypted)
            except Exception:
                token_masked = "****"

        output.append({
            "id": conn.id,
            "name": conn.name,
            "service": conn.service,
            "category": conn.category,
            "base_url": conn.base_url or "",
            "api_key_masked": api_key_masked,
            "token_masked": token_masked,
            "cred_path": conn.cred_path or "",
            "enabled": conn.enabled,
            "status": status,
            "latency_avg_ms": round(avg_latency, 1),
            "requests_24h": total,
            "errors_24h": error_count
        })

    return output


async def get_cost_configs(db: AsyncSession) -> list:
    """All cost configurations."""
    result = await db.execute(select(CostConfig).order_by(CostConfig.provider, CostConfig.model))
    rows = result.scalars().all()
    return [{
        "id": r.id,
        "model": r.model,
        "provider": r.provider,
        "input_cost_per_million": r.input_cost_per_million,
        "output_cost_per_million": r.output_cost_per_million
    } for r in rows]


async def get_budget_limits(db: AsyncSession) -> dict:
    """Current budget limits. Creates default row if none exists."""
    result = await db.execute(select(BudgetLimit).limit(1))
    row = result.scalar_one_or_none()
    if row is None:
        row = BudgetLimit()
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return {
        "id": row.id,
        "daily_limit_usd": row.daily_limit_usd,
        "weekly_limit_usd": row.weekly_limit_usd,
        "monthly_limit_usd": row.monthly_limit_usd
    }


async def get_estimated_costs(db: AsyncSession, period: str = "daily") -> dict:
    """Estimated costs for the given period."""
    if period == "daily":
        since = datetime.now(timezone.utc) - timedelta(days=1)
    elif period == "weekly":
        since = datetime.now(timezone.utc) - timedelta(days=7)
    else:  # monthly
        since = datetime.now(timezone.utc) - timedelta(days=30)

    result = await db.execute(
        select(func.sum(Request.cost_usd).label("total"))
        .where(Request.timestamp >= since)
    )
    row = result.one()
    return {
        "estimated_cost_usd": round(row.total or 0.0, 6),
        "period": period
    }
