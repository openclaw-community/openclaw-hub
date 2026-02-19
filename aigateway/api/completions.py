"""
Completion API endpoints — with retry, fallback, and budget enforcement.
"""

import asyncio
import uuid
from datetime import timezone
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..providers.base import CompletionRequest, CompletionResponse
from ..providers.health import tracker as health_tracker
from ..storage.database import get_session
from ..storage.models import Connection, Request
from ..dashboard.data import get_spend_by_connection, _compute_budget_status
from ..config import settings
import structlog

logger = structlog.get_logger()
router = APIRouter()


def get_provider_manager():
    from ..main import provider_manager
    if provider_manager is None:
        raise HTTPException(status_code=503, detail="Provider manager not initialized")
    return provider_manager


def _parse_fallback_rules() -> dict[str, str]:
    """Parse FALLBACK_RULES env var: "openai:anthropic,anthropic:openai" → dict."""
    rules = {}
    for part in (settings.fallback_rules or "").split(","):
        part = part.strip()
        if ":" in part:
            primary, fallback = part.split(":", 1)
            rules[primary.strip()] = fallback.strip()
    return rules


def _retryable_status(exc: Exception) -> int | None:
    """Extract HTTP status code from an exception if it's a retryable error."""
    import httpx
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code
    # OpenAI SDK errors
    try:
        from openai import APIStatusError
        if isinstance(exc, APIStatusError):
            return exc.status_code
    except ImportError:
        pass
    # Anthropic SDK errors
    try:
        from anthropic import APIStatusError as AnthropicStatusError
        if isinstance(exc, AnthropicStatusError):
            return exc.status_code
    except ImportError:
        pass
    return None


async def _check_budget(db: AsyncSession, provider_name: str) -> dict | None:
    """Return budget error dict if provider is blocked, else None."""
    result = await db.execute(
        select(Connection).where(Connection.service == provider_name).limit(1)
    )
    conn = result.scalar_one_or_none()
    if conn is None:
        return None

    spend_by_service = await get_spend_by_connection(db)
    spend = spend_by_service.get(provider_name, {"daily": 0.0, "weekly": 0.0, "monthly": 0.0})
    status = _compute_budget_status(conn, spend)
    if not status["budget_blocked"]:
        return None

    reason = status["budget_blocked_reason"]
    limit_usd = status.get(f"{reason}_limit_usd", 0.0)
    spent_usd = status.get(f"{reason}_spent_usd", 0.0)
    resets_at = status.get("budget_resets_at", "unknown")

    # Check for available fallback
    fallback_rules = _parse_fallback_rules()
    fallback = fallback_rules.get(provider_name)
    fallback_available = bool(fallback and fallback in (getattr(_get_manager_instance(), 'providers', {}) or {}))

    return {
        "error": {
            "type": "budget_exceeded",
            "message": (
                f"{conn.name} {reason} budget limit reached "
                f"(${spent_usd:.2f}/${limit_usd:.2f}). "
                f"Requests to this provider are blocked until the budget period resets."
            ),
            "connection": provider_name,
            "connection_id": conn.id,
            "limit_type": reason,
            "limit_usd": limit_usd,
            "spent_usd": spent_usd,
            "resets_at": resets_at,
            "fallback_available": fallback_available,
            "fallback_provider": fallback if fallback_available else None,
        }
    }


def _get_manager_instance():
    from ..main import provider_manager
    return provider_manager


async def _complete_with_retry(
    manager,
    request: CompletionRequest,
    provider_name: str,
) -> tuple[CompletionResponse | None, Exception | None]:
    """
    Attempt a completion with exponential-backoff retries for transient errors.
    Returns (response, None) on success, or (None, last_exception) on total failure.
    """
    if not settings.retry_enabled:
        try:
            resp = await manager.complete_with_provider(request, provider_name)
            return resp, None
        except Exception as e:
            return None, e

    retryable_codes = {int(c.strip()) for c in settings.retry_on_status_codes.split(",") if c.strip()}
    delays = [
        settings.retry_backoff_base * (settings.retry_backoff_multiplier ** i)
        for i in range(settings.retry_max_attempts - 1)
    ]

    last_exc = None
    for attempt in range(settings.retry_max_attempts):
        try:
            resp = await manager.complete_with_provider(request, provider_name)
            await health_tracker.record_success(provider_name)
            return resp, None
        except Exception as exc:
            last_exc = exc
            status = _retryable_status(exc)
            is_retryable = status in retryable_codes if status else True  # unknown error → retry

            if is_retryable and attempt < settings.retry_max_attempts - 1:
                delay = delays[attempt]
                logger.warning(
                    "completion_retry",
                    provider=provider_name,
                    attempt=attempt + 1,
                    status_code=status,
                    delay_s=delay,
                )
                await asyncio.sleep(delay)
            else:
                break

    await health_tracker.record_failure(provider_name, str(last_exc))
    return None, last_exc


@router.post("/v1/chat/completions")
async def create_completion(
    request: CompletionRequest,
    db: AsyncSession = Depends(get_session),
    manager=Depends(get_provider_manager),
):
    """
    OpenAI-compatible chat completion endpoint.
    Applies budget enforcement, retry with backoff, and fallback routing.
    """
    provider_name = manager.route_model(request.model)
    fallback_rules = _parse_fallback_rules()
    used_fallback = False
    original_provider = provider_name

    # ── Budget check ──────────────────────────────────────────────────────────
    budget_error = await _check_budget(db, provider_name)
    if budget_error:
        # Try fallback if budget-blocked
        fallback = fallback_rules.get(provider_name)
        if fallback and fallback in manager.providers:
            logger.info("budget_fallback_routing", original=provider_name, fallback=fallback)
            provider_name = fallback
            used_fallback = True
        else:
            logger.warning("completion_blocked_budget", provider=original_provider)
            return JSONResponse(status_code=429, content=budget_error)

    # ── Primary attempt with retry ────────────────────────────────────────────
    response, error = await _complete_with_retry(manager, request, provider_name)

    # ── Fallback on failure ───────────────────────────────────────────────────
    if error and not used_fallback:
        fallback = fallback_rules.get(provider_name)
        if fallback and fallback in manager.providers:
            logger.warning(
                "completion_fallback_routing",
                original=provider_name,
                fallback=fallback,
                reason=str(error),
            )
            response, error = await _complete_with_retry(manager, request, fallback)
            if response:
                used_fallback = True
                provider_name = fallback

    if error:
        logger.error("completion_failed", provider=original_provider, error=str(error))
        raise HTTPException(status_code=502, detail=f"Provider '{original_provider}' failed: {str(error)}")

    # ── Log to DB ─────────────────────────────────────────────────────────────
    log_entry = Request(
        id=str(uuid.uuid4()),
        workflow_name="direct_completion",
        model=response.model,
        provider=provider_name,
        prompt_tokens=response.prompt_tokens,
        completion_tokens=response.completion_tokens,
        total_tokens=response.total_tokens,
        cost_usd=response.cost_usd,
        latency_ms=response.latency_ms,
        success=True,
    )
    db.add(log_entry)
    await db.commit()

    logger.info(
        "completion_success",
        model=response.model,
        provider=provider_name,
        fallback=used_fallback,
        tokens=response.total_tokens,
        cost_usd=response.cost_usd,
        latency_ms=response.latency_ms,
    )

    # Build response — attach fallback headers if routing changed
    resp_data = response.model_dump()
    headers = {}
    if used_fallback:
        headers["X-Hub-Fallback"] = "true"
        headers["X-Hub-Original-Provider"] = original_provider
        headers["X-Hub-Actual-Provider"] = provider_name

    from fastapi.responses import JSONResponse as _JSONResponse
    return _JSONResponse(content=resp_data, headers=headers)


@router.get("/v1/models")
async def list_models(manager = Depends(get_provider_manager)):
    """List available models from all providers"""
    models = await manager.list_all_models()
    return {"models": models}
