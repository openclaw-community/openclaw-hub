"""
Utility for logging non-LLM API calls to the api_calls table.

Usage in any client:

    from ..dashboard.api_logger import log_api_call

    start = time.monotonic()
    response = await client.post(url, ...)
    await log_api_call(
        service="github",
        operation="create_issue",
        endpoint="/repos/owner/repo/issues",
        method="POST",
        status_code=response.status_code,
        success=response.status_code < 400,
        latency_ms=(time.monotonic() - start) * 1000,
    )

Logging failures are silently swallowed — a logging error must never break the
actual API call.
"""

import json
import structlog
from typing import Optional
from ..storage.database import async_session
from ..storage.models import ApiCall

logger = structlog.get_logger()


async def log_api_call(
    service: str,
    operation: str,
    endpoint: str = "",
    method: str = "GET",
    status_code: Optional[int] = None,
    success: bool = True,
    error: Optional[str] = None,
    latency_ms: Optional[float] = None,
    request_size_bytes: Optional[int] = None,
    response_size_bytes: Optional[int] = None,
    cost_usd: float = 0.0,
    metadata: Optional[dict] = None,
) -> None:
    """
    Log a non-LLM API call to the api_calls table.

    Opens its own short-lived database session so callers do not need
    an injected session.  Any exception is caught and logged — this
    function must never raise.
    """
    try:
        async with async_session() as session:
            entry = ApiCall(
                service=service,
                operation=operation,
                endpoint=endpoint,
                method=method,
                status_code=status_code,
                success=success,
                error=error,
                latency_ms=latency_ms,
                request_size_bytes=request_size_bytes,
                response_size_bytes=response_size_bytes,
                cost_usd=cost_usd,
                metadata_json=json.dumps(metadata or {}),
            )
            session.add(entry)
            await session.commit()
    except Exception as exc:
        logger.error(
            "api_call_log_failed",
            service=service,
            operation=operation,
            error=str(exc),
        )
