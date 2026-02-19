"""
Webhook notification channel — HTTP POST to a configurable URL.

On failure, logs a warning but does not raise (best-effort delivery).
"""

import structlog
import httpx

logger = structlog.get_logger()


async def send_webhook(payload: dict) -> None:
    """POST the alert payload as JSON to the configured webhook URL."""
    from ...config import settings

    url = settings.alert_webhook_url
    if not url:
        return

    alert_id = payload.get("id", "unknown")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            logger.info("webhook_alert_sent", alert_id=alert_id, status=resp.status_code)
    except Exception as exc:
        logger.warning("webhook_alert_failed", alert_id=alert_id, error=str(exc))
