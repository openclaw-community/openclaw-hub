"""
AlertManager — creates, deduplicates, auto-resolves, and dispatches alerts.

Design notes:
  - All alerts are persisted to the `alerts` table immediately on creation.
  - Deduplication: if an unresolved alert with the same (trigger, connection) pair
    was created within ALERT_DEDUP_WINDOW_MINUTES, the new one is suppressed.
  - Auto-resolve: callers invoke try_resolve() when a condition clears; this sets
    resolved=True + resolved_at on any matching open alerts.
  - Dispatch: after DB write, alert is pushed to enabled channels (webhook, desktop).
    Dashboard channel is implicit — banners poll GET /api/alerts/active from the DB.
"""

import json
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..storage.models import Alert

logger = structlog.get_logger()


def _to_payload(alert: Alert) -> dict:
    """Serialise an Alert row to the standard hub_alert payload dict."""
    return {
        "id": alert.id,
        "type": "hub_alert",
        "severity": alert.severity,
        "trigger": alert.trigger,
        "connection": alert.connection,
        "message": alert.message,
        "details": json.loads(alert.details_json or "{}"),
        "suggested_action": alert.suggested_action,
        "timestamp": (
            alert.created_at.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
            if alert.created_at
            else None
        ),
        "resolved": alert.resolved,
    }


class AlertManager:
    """
    Stateless helper — all state lives in the database.
    Instantiate once as a module-level singleton.
    """

    async def create_alert(
        self,
        db: AsyncSession,
        *,
        alert_id: str,
        severity: str,
        trigger: str,
        connection: str | None,
        message: str,
        details: dict,
        suggested_action: str | None = None,
    ) -> Alert | None:
        """
        Persist and dispatch a new alert, unless deduplicated.
        Returns the created Alert, or None if suppressed by dedup.
        """
        # ── Deduplication check ──────────────────────────────────────────────
        dedup_since = datetime.now(timezone.utc) - timedelta(
            minutes=settings.alert_dedup_window_minutes
        )
        filters = [
            Alert.trigger == trigger,
            Alert.resolved == False,   # noqa: E712
            Alert.created_at >= dedup_since,
        ]
        if connection is not None:
            filters.append(Alert.connection == connection)
        else:
            filters.append(Alert.connection.is_(None))

        existing = await db.execute(select(Alert).where(and_(*filters)).limit(1))
        if existing.scalar_one_or_none() is not None:
            logger.debug(
                "alert_deduplicated",
                trigger=trigger,
                connection=connection,
                dedup_window_minutes=settings.alert_dedup_window_minutes,
            )
            return None

        # ── Persist ──────────────────────────────────────────────────────────
        now = datetime.now(timezone.utc)
        alert = Alert(
            id=alert_id,
            severity=severity,
            trigger=trigger,
            connection=connection,
            message=message,
            details_json=json.dumps(details),
            suggested_action=suggested_action,
            created_at=now,
            resolved=False,
            dismissed=False,
        )
        db.add(alert)
        await db.commit()
        await db.refresh(alert)

        logger.warning(
            "alert_created",
            alert_id=alert_id,
            severity=severity,
            trigger=trigger,
            connection=connection,
            message=message,
        )

        # ── Dispatch to active channels ───────────────────────────────────────
        await self._dispatch(alert)
        return alert

    async def try_resolve(
        self, db: AsyncSession, trigger: str, connection: str | None
    ) -> int:
        """
        Auto-resolve any open alerts matching (trigger, connection).
        Returns the number of alerts resolved.
        """
        filters = [Alert.trigger == trigger, Alert.resolved == False]  # noqa: E712
        if connection is not None:
            filters.append(Alert.connection == connection)
        else:
            filters.append(Alert.connection.is_(None))

        result = await db.execute(select(Alert).where(and_(*filters)))
        alerts = result.scalars().all()
        if not alerts:
            return 0

        now = datetime.now(timezone.utc)
        for alert in alerts:
            alert.resolved = True
            alert.resolved_at = now

        await db.commit()
        count = len(alerts)
        logger.info(
            "alerts_auto_resolved",
            count=count,
            trigger=trigger,
            connection=connection,
        )
        return count

    async def _dispatch(self, alert: Alert) -> None:
        """Push alert to all configured notification channels."""
        payload = _to_payload(alert)

        # Webhook
        if settings.alert_webhook_url:
            from .channels.webhook import send_webhook
            await send_webhook(payload)

        # Desktop (macOS / Linux — best-effort, no crash on failure)
        if settings.alert_desktop_notify:
            from .channels.desktop import send_desktop_notification
            await send_desktop_notification(alert.message, alert.severity)


# Module-level singleton
alert_manager = AlertManager()
