"""
Completion API endpoints
"""

from datetime import timezone
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..providers.base import CompletionRequest, CompletionResponse
from ..storage.database import get_session
from ..storage.models import Connection, Request
from ..dashboard.data import get_spend_by_connection, _compute_budget_status
import uuid
import structlog

logger = structlog.get_logger()
router = APIRouter()


def get_provider_manager():
    """Get provider manager from app state"""
    from ..main import provider_manager
    if provider_manager is None:
        raise HTTPException(status_code=503, detail="Provider manager not initialized")
    return provider_manager


async def _check_budget(db: AsyncSession, provider_name: str) -> dict | None:
    """
    Check whether the connection for `provider_name` is budget-blocked.
    Returns None if the request can proceed, or a dict with error details if blocked.
    """
    result = await db.execute(
        select(Connection).where(Connection.service == provider_name).limit(1)
    )
    conn = result.scalar_one_or_none()
    if conn is None:
        return None  # No connection record — allow through

    spend_by_service = await get_spend_by_connection(db)
    spend = spend_by_service.get(provider_name, {"daily": 0.0, "weekly": 0.0, "monthly": 0.0})
    status = _compute_budget_status(conn, spend)

    if not status["budget_blocked"]:
        return None

    reason = status["budget_blocked_reason"]  # e.g. "daily"
    limit_usd = status.get(f"{reason}_limit_usd", 0.0)
    spent_usd = status.get(f"{reason}_spent_usd", 0.0)
    resets_at = status.get("budget_resets_at", "unknown")

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
            "fallback_available": False,  # Fallback routing will be added in Issue #29
        }
    }


@router.post("/v1/chat/completions", response_model=CompletionResponse)
async def create_completion(
    request: CompletionRequest,
    db: AsyncSession = Depends(get_session),
    manager = Depends(get_provider_manager)
) -> CompletionResponse:
    """
    OpenAI-compatible chat completion endpoint.
    Routes to appropriate provider based on model, subject to per-connection budget enforcement.
    """
    try:
        # Determine provider before routing so we can check budget
        provider_name = manager.route_model(request.model)

        # Budget enforcement check (Issue #32)
        budget_error = await _check_budget(db, provider_name)
        if budget_error:
            logger.warning(
                "completion_blocked_budget",
                provider=provider_name,
                reason=budget_error["error"]["limit_type"],
            )
            return JSONResponse(status_code=429, content=budget_error)

        # Route to appropriate provider
        response = await manager.complete(request)

        # Log to database
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
            success=True
        )
        db.add(log_entry)
        await db.commit()

        logger.info(
            "completion_success",
            model=response.model,
            provider=provider_name,
            tokens=response.total_tokens,
            cost_usd=response.cost_usd,
            latency_ms=response.latency_ms
        )

        return response

    except Exception as e:
        logger.error("completion_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v1/models")
async def list_models(manager = Depends(get_provider_manager)):
    """List available models from all providers"""
    models = await manager.list_all_models()
    return {"models": models}
