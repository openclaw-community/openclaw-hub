"""
Alert API endpoints (Issue #29).

GET  /api/alerts          — list alerts (filters: resolved, connection, limit)
GET  /api/alerts/active   — shortcut: unresolved + undismissed only
POST /api/alerts/{id}/dismiss — mark alert dismissed from dashboard banner
GET  /api/alerts/config   — current alert config
PUT  /api/alerts/config   — update alert thresholds at runtime (in-memory; restart persists)
"""

import json
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..storage.database import get_session
from ..storage.models import Alert

logger = structlog.get_logger()
router = APIRouter(prefix="/api/alerts", tags=["alerts"])


# ---------------------------------------------------------------------------
# Serialisation helper
# ---------------------------------------------------------------------------

def _serialize(a: Alert) -> dict:
    return {
        "id": a.id,
        "type": "hub_alert",
        "severity": a.severity,
        "trigger": a.trigger,
        "connection": a.connection,
        "message": a.message,
        "details": json.loads(a.details_json or "{}"),
        "suggested_action": a.suggested_action,
        "created_at": a.created_at.isoformat() + "Z" if a.created_at else None,
        "resolved": a.resolved,
        "resolved_at": a.resolved_at.isoformat() + "Z" if a.resolved_at else None,
        "dismissed": a.dismissed,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("")
async def list_alerts(
    resolved: Optional[bool] = None,
    connection: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_session),
):
    """List alerts with optional filters."""
    filters = []
    if resolved is not None:
        filters.append(Alert.resolved == resolved)
    if connection:
        filters.append(Alert.connection == connection)

    q = select(Alert).order_by(Alert.created_at.desc()).limit(min(limit, 200))
    if filters:
        q = q.where(and_(*filters))

    result = await db.execute(q)
    alerts = result.scalars().all()
    return {"alerts": [_serialize(a) for a in alerts], "count": len(alerts)}


@router.get("/active")
async def list_active_alerts(db: AsyncSession = Depends(get_session)):
    """Shortcut: unresolved + undismissed alerts only (used by dashboard banner poll)."""
    result = await db.execute(
        select(Alert)
        .where(Alert.resolved == False)    # noqa: E712
        .where(Alert.dismissed == False)   # noqa: E712
        .order_by(Alert.created_at.desc())
    )
    alerts = result.scalars().all()
    return {"alerts": [_serialize(a) for a in alerts], "count": len(alerts)}


@router.post("/{alert_id}/dismiss")
async def dismiss_alert(alert_id: str, db: AsyncSession = Depends(get_session)):
    """Mark an alert as dismissed — hides it from the dashboard banner."""
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if alert is None:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found")
    alert.dismissed = True
    await db.commit()
    logger.info("alert_dismissed", alert_id=alert_id)
    return {"ok": True, "alert_id": alert_id}


@router.get("/config")
async def get_alert_config():
    """Return current alert configuration values."""
    return {
        "alert_enabled": settings.alert_enabled,
        "alert_check_interval_seconds": settings.alert_check_interval_seconds,
        "alert_consecutive_error_threshold": settings.alert_consecutive_error_threshold,
        "alert_latency_multiplier": settings.alert_latency_multiplier,
        "alert_latency_window_minutes": settings.alert_latency_window_minutes,
        "alert_budget_threshold_percent": settings.alert_budget_threshold_percent,
        "alert_dedup_window_minutes": settings.alert_dedup_window_minutes,
        "alert_webhook_url": settings.alert_webhook_url,
        "alert_desktop_notify": settings.alert_desktop_notify,
    }


class AlertConfigPatch(BaseModel):
    alert_enabled: Optional[bool] = None
    alert_check_interval_seconds: Optional[int] = None
    alert_consecutive_error_threshold: Optional[int] = None
    alert_latency_multiplier: Optional[float] = None
    alert_latency_window_minutes: Optional[int] = None
    alert_budget_threshold_percent: Optional[float] = None
    alert_dedup_window_minutes: Optional[int] = None
    alert_webhook_url: Optional[str] = None
    alert_desktop_notify: Optional[bool] = None


@router.put("/config")
async def update_alert_config(patch: AlertConfigPatch):
    """
    Update alert thresholds at runtime (in-memory only; changes survive until Hub restarts).
    To persist permanently, add the updated values to .env.
    """
    updated = {}
    for field, value in patch.model_dump(exclude_none=True).items():
        if hasattr(settings, field):
            setattr(settings, field, value)
            updated[field] = value

    logger.info("alert_config_updated", changes=updated)
    return {"ok": True, "updated": updated, "note": "Changes are in-memory only; add to .env to persist."}
