"""
Desktop notification channel — macOS (osascript) and Linux (notify-send).

Best-effort: silently skips if the OS command is unavailable or fails.
Never raises — a missing notification should never crash Hub.
"""

import asyncio
import platform

import structlog

logger = structlog.get_logger()

# Sanitise strings going into shell commands
def _safe(s: str) -> str:
    return s.replace('"', "'").replace("\n", " ").replace("\r", "")


async def send_desktop_notification(message: str, severity: str) -> None:
    """Fire a desktop notification for the given alert message and severity."""
    title = f"OpenClaw Hub — {severity.capitalize()} Alert"
    system = platform.system()

    try:
        if system == "Darwin":
            script = (
                f'display notification "{_safe(message)}" '
                f'with title "{_safe(title)}"'
            )
            proc = await asyncio.create_subprocess_exec(
                "osascript", "-e", script,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.wait(), timeout=5.0)
            logger.debug("desktop_notification_sent", system="darwin", severity=severity)

        elif system == "Linux":
            proc = await asyncio.create_subprocess_exec(
                "notify-send",
                _safe(title),
                _safe(message),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.wait(), timeout=5.0)
            logger.debug("desktop_notification_sent", system="linux", severity=severity)

        # Windows / unknown: silently skip (no desktop notification support in v1)

    except asyncio.TimeoutError:
        logger.debug("desktop_notification_timeout", severity=severity)
    except Exception as exc:
        logger.debug("desktop_notification_failed", error=str(exc))
