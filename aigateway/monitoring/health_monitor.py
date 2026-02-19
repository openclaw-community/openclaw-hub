"""
HealthMonitor — background asyncio task that checks provider health and triggers alerts.

Detection methods (all query the existing `requests` / `connections` tables):
  1. Consecutive errors     — last N requests for a provider all failed
  2. Latency spike          — recent avg latency >= baseline_avg * multiplier
  3. Budget threshold       — daily spend >= threshold_pct of daily_limit_usd

Each check calls alert_manager.create_alert() on condition entry and
alert_manager.try_resolve() when the condition clears.
"""

import asyncio
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..storage.database import async_session
from ..storage.models import Connection, Request
from .alert_manager import alert_manager

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Alert ID helper
# ---------------------------------------------------------------------------

def _make_alert_id(trigger: str, connection: str | None) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    conn_part = (connection or "system").replace(" ", "_")
    return f"alert_{ts}_{conn_part}_{trigger}"


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

async def _check_consecutive_errors(
    db: AsyncSession, provider: str, threshold: int
) -> bool:
    """
    Return True if the most recent `threshold` requests for this provider all failed.
    Returns False if fewer than `threshold` records exist (insufficient data).
    """
    result = await db.execute(
        select(Request.success)
        .where(Request.provider == provider)
        .order_by(Request.timestamp.desc())
        .limit(threshold)
    )
    rows = result.scalars().all()
    if len(rows) < threshold:
        return False
    return all(not r for r in rows)


async def _check_latency_spike(
    db: AsyncSession,
    provider: str,
    window_minutes: int,
    multiplier: float,
) -> tuple[bool, float, float]:
    """
    Compare average latency over the last `window_minutes` to the 1-hour rolling baseline.
    Only considers successful requests (errors skew latency).
    Returns (spike_detected, recent_avg_ms, baseline_avg_ms).
    """
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(minutes=window_minutes)
    baseline_start = now - timedelta(hours=1)

    recent_result = await db.execute(
        select(func.avg(Request.latency_ms))
        .where(Request.provider == provider)
        .where(Request.timestamp >= window_start)
        .where(Request.success == True)   # noqa: E712
    )
    baseline_result = await db.execute(
        select(func.avg(Request.latency_ms))
        .where(Request.provider == provider)
        .where(Request.timestamp >= baseline_start)
        .where(Request.success == True)   # noqa: E712
    )

    recent_avg = recent_result.scalar() or 0.0
    baseline_avg = baseline_result.scalar() or 0.0

    # Can't determine a spike without a meaningful baseline or recent sample
    if baseline_avg == 0.0 or recent_avg == 0.0:
        return False, recent_avg, baseline_avg

    return recent_avg >= (baseline_avg * multiplier), recent_avg, baseline_avg


async def _check_budget_threshold(
    db: AsyncSession,
    conn: Connection,
    threshold_pct: float,
) -> tuple[bool, float, float]:
    """
    Return True if today's spend for this connection >= threshold_pct of daily_limit_usd.
    Returns (exceeded, spent_usd, limit_usd).
    """
    if not conn.daily_limit_usd or conn.daily_limit_usd <= 0:
        return False, 0.0, 0.0

    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    result = await db.execute(
        select(func.sum(Request.cost_usd))
        .where(Request.provider == conn.service)
        .where(Request.timestamp >= today_start)
    )
    spent = result.scalar() or 0.0
    limit = conn.daily_limit_usd
    exceeded = spent >= (limit * threshold_pct / 100.0)
    return exceeded, spent, limit


# ---------------------------------------------------------------------------
# Main check runner
# ---------------------------------------------------------------------------

async def run_health_checks() -> None:
    """
    Run all health checks for all enabled connections and create/resolve alerts.
    Executed once per interval by health_monitor_loop().
    """
    async with async_session() as db:
        conns_result = await db.execute(
            select(Connection).where(Connection.enabled == True)  # noqa: E712
        )
        connections = conns_result.scalars().all()

        for conn in connections:
            provider = conn.service

            # ── 1. Consecutive errors ──────────────────────────────────────
            trigger = "consecutive_errors"
            threshold = settings.alert_consecutive_error_threshold
            try:
                exceeded = await _check_consecutive_errors(db, provider, threshold)
            except Exception as e:
                logger.warning("health_check_error", check=trigger, provider=provider, error=str(e))
                continue

            if exceeded:
                await alert_manager.create_alert(
                    db,
                    alert_id=_make_alert_id(trigger, provider),
                    severity="error",
                    trigger=trigger,
                    connection=provider,
                    message=(
                        f"{conn.name} has {threshold} consecutive request failures."
                    ),
                    details={
                        "error_count": threshold,
                        "threshold": threshold,
                    },
                    suggested_action="check_provider_status",
                )
            else:
                await alert_manager.try_resolve(db, trigger, provider)

            # ── 2. Latency spike ──────────────────────────────────────────
            trigger = "latency_spike"
            try:
                spike, recent_avg, baseline_avg = await _check_latency_spike(
                    db,
                    provider,
                    settings.alert_latency_window_minutes,
                    settings.alert_latency_multiplier,
                )
            except Exception as e:
                logger.warning("health_check_error", check=trigger, provider=provider, error=str(e))
                continue

            if spike:
                await alert_manager.create_alert(
                    db,
                    alert_id=_make_alert_id(trigger, provider),
                    severity="warning",
                    trigger=trigger,
                    connection=provider,
                    message=(
                        f"{conn.name} latency spike: {recent_avg:.0f}ms over the last "
                        f"{settings.alert_latency_window_minutes}m "
                        f"(baseline: {baseline_avg:.0f}ms, "
                        f"threshold: {settings.alert_latency_multiplier}×)."
                    ),
                    details={
                        "recent_avg_ms": round(recent_avg, 1),
                        "baseline_avg_ms": round(baseline_avg, 1),
                        "multiplier_threshold": settings.alert_latency_multiplier,
                        "window_minutes": settings.alert_latency_window_minutes,
                    },
                    suggested_action="check_provider_status",
                )
            else:
                await alert_manager.try_resolve(db, trigger, provider)

            # ── 3. Budget threshold ───────────────────────────────────────
            trigger = "budget_threshold"
            try:
                bexceeded, spent, limit = await _check_budget_threshold(
                    db, conn, settings.alert_budget_threshold_percent
                )
            except Exception as e:
                logger.warning("health_check_error", check=trigger, provider=provider, error=str(e))
                continue

            if bexceeded:
                pct = (spent / limit * 100.0) if limit > 0 else 0.0
                await alert_manager.create_alert(
                    db,
                    alert_id=_make_alert_id(trigger, provider),
                    severity="warning",
                    trigger=trigger,
                    connection=provider,
                    message=(
                        f"{conn.name} daily budget at {pct:.0f}%: "
                        f"${spent:.2f} of ${limit:.2f} limit reached."
                    ),
                    details={
                        "spent_usd": round(spent, 4),
                        "limit_usd": round(limit, 4),
                        "percent": round(pct, 1),
                        "threshold_percent": settings.alert_budget_threshold_percent,
                    },
                    suggested_action="check_budget",
                )
            else:
                await alert_manager.try_resolve(db, trigger, provider)

        logger.debug("health_checks_complete", connection_count=len(connections))


# ---------------------------------------------------------------------------
# Background loop
# ---------------------------------------------------------------------------

async def health_monitor_loop() -> None:
    """
    Background asyncio task — started from main.py startup_event().
    Sleeps for alert_check_interval_seconds, then runs all checks.
    Runs immediately on first iteration after the initial sleep (avoids
    spamming alerts on every Hub restart).
    """
    while True:
        await asyncio.sleep(settings.alert_check_interval_seconds)
        if not settings.alert_enabled:
            continue
        try:
            await run_health_checks()
        except Exception as e:
            logger.error("health_monitor_loop_error", error=str(e))
