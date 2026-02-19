"""
Data access layer for dashboard queries.
All functions are async — they use AsyncSession.
"""

from datetime import datetime, timedelta, timezone
from sqlalchemy import func, select, desc, text, case
from sqlalchemy.ext.asyncio import AsyncSession
from aigateway.storage.models import Request, Connection, CostConfig, BudgetLimit, ApiCall

# Services whose traffic is recorded in the `requests` table (LLM completions).
# All other services are recorded in the `api_calls` table.
LLM_PROVIDER_SERVICES = {'openai', 'anthropic', 'ollama', 'openrouter', 'lmstudio', 'custom'}
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
    """All connections with masked credentials, computed health stats, and budget status."""
    result = await db.execute(select(Connection).order_by(Connection.id))
    connections = result.scalars().all()

    since_24h = datetime.now(timezone.utc) - timedelta(hours=24)

    # Fetch all spend data in one pass
    spend_by_service = await get_spend_by_connection(db)

    output = []

    for conn in connections:
        # LLM providers log to the `requests` table; all others log to `api_calls`.
        if conn.service in LLM_PROVIDER_SERVICES:
            req_result = await db.execute(
                select(
                    func.count(Request.id).label("total"),
                    func.sum(case((Request.success == False, 1), else_=0)).label("errors"),
                    func.avg(Request.latency_ms).label("avg_latency"),
                )
                .where(Request.provider == conn.service)
                .where(Request.timestamp >= since_24h)
            )
        else:
            req_result = await db.execute(
                select(
                    func.count(ApiCall.id).label("total"),
                    func.sum(case((ApiCall.success == False, 1), else_=0)).label("errors"),
                    func.avg(ApiCall.latency_ms).label("avg_latency"),
                )
                .where(ApiCall.service == conn.service)
                .where(ApiCall.timestamp >= since_24h)
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

        spend = spend_by_service.get(conn.service, {"daily": 0.0, "weekly": 0.0, "monthly": 0.0})
        budget_status = _compute_budget_status(conn, spend)

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
            "errors_24h": error_count,
            **budget_status,
        })

    return output


async def get_cost_configs(db: AsyncSession) -> list:
    """All cost configurations, ordered by connection then model."""
    result = await db.execute(
        select(CostConfig).order_by(CostConfig.connection_id.nullslast(), CostConfig.provider, CostConfig.model)
    )
    rows = result.scalars().all()
    return [{
        "id": r.id,
        "connection_id": r.connection_id,
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


async def get_recent_api_calls(db: AsyncSession, limit: int = 50) -> list:
    """Most recent N non-LLM API calls ordered by timestamp DESC."""
    result = await db.execute(
        select(ApiCall)
        .order_by(desc(ApiCall.timestamp))
        .limit(min(limit, 200))
    )
    rows = result.scalars().all()
    return [{
        "id": str(r.id),
        "created_at": r.timestamp.isoformat() + "Z" if r.timestamp else None,
        "service": r.service,
        "operation": r.operation,
        "endpoint": r.endpoint or "",
        "method": r.method or "GET",
        "status_code": r.status_code,
        "cost_usd": round(r.cost_usd or 0.0, 6),
        "latency_ms": r.latency_ms or 0,
        "success": r.success,
        "error": r.error,
    } for r in rows]


async def get_api_call_count_24h(db: AsyncSession) -> int:
    """Count of non-LLM API calls in the last 24 hours."""
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    result = await db.execute(
        select(func.count(ApiCall.id)).where(ApiCall.timestamp >= since)
    )
    return result.scalar() or 0


async def get_api_calls_by_service_daily(db: AsyncSession, days: int = 30) -> list:
    """Non-LLM API call counts aggregated by day and service for the last N days."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(
            func.date(ApiCall.timestamp).label("date"),
            ApiCall.service,
            func.count(ApiCall.id).label("total_requests"),
        )
        .where(ApiCall.timestamp >= since)
        .group_by(func.date(ApiCall.timestamp), ApiCall.service)
        .order_by(func.date(ApiCall.timestamp).asc())
    )
    rows = result.all()
    return [{"date": str(r.date), "service": r.service, "total_requests": r.total_requests} for r in rows]


async def get_api_calls_by_service_weekly(db: AsyncSession, weeks: int = 12) -> list:
    """Non-LLM API call counts aggregated by ISO week and service."""
    since = datetime.now(timezone.utc) - timedelta(weeks=weeks)
    result = await db.execute(
        select(
            func.strftime('%Y-W%W', ApiCall.timestamp).label("week"),
            ApiCall.service,
            func.count(ApiCall.id).label("total_requests"),
        )
        .where(ApiCall.timestamp >= since)
        .group_by(func.strftime('%Y-W%W', ApiCall.timestamp), ApiCall.service)
        .order_by(func.strftime('%Y-W%W', ApiCall.timestamp).asc())
    )
    rows = result.all()
    return [{"week": r.week, "service": r.service, "total_requests": r.total_requests} for r in rows]


async def get_api_calls_by_service_monthly(db: AsyncSession, months: int = 6) -> list:
    """Non-LLM API call counts aggregated by month and service."""
    since = datetime.now(timezone.utc) - timedelta(days=months * 30)
    result = await db.execute(
        select(
            func.strftime('%Y-%m', ApiCall.timestamp).label("month"),
            ApiCall.service,
            func.count(ApiCall.id).label("total_requests"),
        )
        .where(ApiCall.timestamp >= since)
        .group_by(func.strftime('%Y-%m', ApiCall.timestamp), ApiCall.service)
        .order_by(func.strftime('%Y-%m', ApiCall.timestamp).asc())
    )
    rows = result.all()
    return [{"month": r.month, "service": r.service, "total_requests": r.total_requests} for r in rows]


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


# ---------------------------------------------------------------------------
# Budget period helpers
# ---------------------------------------------------------------------------

def _period_start_utc(period: str) -> datetime:
    """Return the UTC start of the current calendar period (daily/weekly/monthly)."""
    now = datetime.now(timezone.utc)
    if period == "daily":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "weekly":
        # Monday of the current week
        monday = now - timedelta(days=now.weekday())
        return monday.replace(hour=0, minute=0, second=0, microsecond=0)
    else:  # monthly
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _period_reset_utc(period: str) -> datetime:
    """Return the UTC time when the current period resets (next period start)."""
    import calendar
    now = datetime.now(timezone.utc)
    if period == "daily":
        return (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "weekly":
        days_until_monday = 7 - now.weekday()
        return (now + timedelta(days=days_until_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
    else:  # monthly
        last_day = calendar.monthrange(now.year, now.month)[1]
        next_month_start = now.replace(day=last_day) + timedelta(days=1)
        return next_month_start.replace(hour=0, minute=0, second=0, microsecond=0)


async def get_spend_by_connection(db: AsyncSession) -> dict:
    """
    Returns per-connection spend for each calendar period (daily/weekly/monthly).
    Keys are connection service names; values are dicts with daily/weekly/monthly spend in USD.

    Spend is calculated by joining requests against cost_configs on model+provider,
    then summing (prompt_tokens * input_cost + completion_tokens * output_cost) / 1_000_000.
    Falls back to Request.cost_usd when no cost config matches.
    """
    result = {}

    # Get all connections to initialise the dict
    conns_result = await db.execute(select(Connection))
    connections = conns_result.scalars().all()
    conn_by_service = {c.service: c for c in connections}

    for period in ("daily", "weekly", "monthly"):
        since = _period_start_utc(period)

        # Sum Request.cost_usd per provider within this period
        spend_result = await db.execute(
            select(
                Request.provider,
                func.sum(Request.cost_usd).label("total_cost"),
            )
            .where(Request.timestamp >= since)
            .where(Request.provider.isnot(None))
            .group_by(Request.provider)
        )
        for row in spend_result.all():
            service = row.provider
            if service not in result:
                result[service] = {"daily": 0.0, "weekly": 0.0, "monthly": 0.0}
            result[service][period] = round(row.total_cost or 0.0, 6)

        # Also sum ApiCall.cost_usd per service for non-LLM providers
        api_spend_result = await db.execute(
            select(
                ApiCall.service,
                func.sum(ApiCall.cost_usd).label("total_cost"),
            )
            .where(ApiCall.timestamp >= since)
            .where(ApiCall.service.isnot(None))
            .group_by(ApiCall.service)
        )
        for row in api_spend_result.all():
            service = row.service
            if service not in result:
                result[service] = {"daily": 0.0, "weekly": 0.0, "monthly": 0.0}
            result[service][period] = round(
                result[service].get(period, 0.0) + (row.total_cost or 0.0), 6
            )

    return result


def _compute_budget_status(conn: Connection, spend: dict) -> dict:
    """
    Given a Connection row and its spend dict {daily, weekly, monthly},
    compute budget_blocked, budget_blocked_reason, and override status.
    Returns a dict of budget fields to merge into the connection response.
    """
    now = datetime.now(timezone.utc)
    daily_spent = spend.get("daily", 0.0)
    weekly_spent = spend.get("weekly", 0.0)
    monthly_spent = spend.get("monthly", 0.0)

    # Check override
    override_active = (
        conn.budget_override_until is not None
        and conn.budget_override_until.replace(tzinfo=timezone.utc) > now
    )

    blocked_periods = []
    if conn.daily_limit_usd is not None and daily_spent >= conn.daily_limit_usd:
        blocked_periods.append(("daily", conn.daily_limit_usd, daily_spent))
    if conn.weekly_limit_usd is not None and weekly_spent >= conn.weekly_limit_usd:
        blocked_periods.append(("weekly", conn.weekly_limit_usd, weekly_spent))
    if conn.monthly_limit_usd is not None and monthly_spent >= conn.monthly_limit_usd:
        blocked_periods.append(("monthly", conn.monthly_limit_usd, monthly_spent))

    budget_blocked = bool(blocked_periods) and not override_active
    budget_blocked_reason = blocked_periods[0][0] if blocked_periods else None

    # Latest reset time among all blocked periods (most restrictive)
    latest_reset = None
    if blocked_periods:
        latest_reset = max(_period_reset_utc(p[0]) for p in blocked_periods).isoformat() + "Z"

    override_until = None
    if conn.budget_override_until:
        override_until = conn.budget_override_until.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")

    return {
        "daily_limit_usd": conn.daily_limit_usd,
        "weekly_limit_usd": conn.weekly_limit_usd,
        "monthly_limit_usd": conn.monthly_limit_usd,
        "daily_spent_usd": daily_spent,
        "weekly_spent_usd": weekly_spent,
        "monthly_spent_usd": monthly_spent,
        "budget_blocked": budget_blocked,
        "budget_blocked_reason": budget_blocked_reason,
        "budget_resets_at": latest_reset,
        "budget_override_active": override_active,
        "budget_override_until": override_until,
    }


# ---------------------------------------------------------------------------
# Default cost entry creation
# ---------------------------------------------------------------------------

# Map of service -> list of default model names to auto-create at $0.00
DEFAULT_COST_MODELS: dict[str, list[str]] = {
    "openai":      ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
    "anthropic":   ["claude-sonnet", "claude-haiku", "claude-opus"],
    "openrouter":  ["openrouter-default"],
    "getlate":     ["getlate-default"],
    "ollama":      ["ollama-local"],
    "lmstudio":    ["lmstudio-local"],
    "custom":      ["custom-default"],
    # Non-LLM — single $0.00 placeholder for cost visibility
    "elevenlabs":  ["elevenlabs"],
    "github":      ["github"],
    "kie":         ["kie"],
    "sora":        ["sora"],
}


async def create_default_cost_entries(db: AsyncSession, connection_id: int, service: str) -> list[str]:
    """
    Auto-create $0.00 cost entries for all default models for a given service.
    Skips models that already have a cost entry for this connection_id.
    Returns list of model names created.
    """
    from aigateway.storage.models import CostConfig

    models_to_create = DEFAULT_COST_MODELS.get(service, [service])
    created = []

    for model_name in models_to_create:
        # Check for existing entry with this connection_id + model
        existing = await db.execute(
            select(CostConfig).where(
                CostConfig.connection_id == connection_id,
                CostConfig.model == model_name,
            )
        )
        if existing.scalar_one_or_none():
            continue

        entry = CostConfig(
            connection_id=connection_id,
            model=model_name,
            provider=service,
            input_cost_per_million=0.0,
            output_cost_per_million=0.0,
        )
        db.add(entry)
        created.append(model_name)

    if created:
        await db.commit()

    return created
