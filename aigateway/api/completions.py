"""
Completion API endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ..providers.base import CompletionRequest, CompletionResponse
from ..storage.database import get_session
from ..storage.models import Request
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


@router.post("/v1/chat/completions", response_model=CompletionResponse)
async def create_completion(
    request: CompletionRequest,
    db: AsyncSession = Depends(get_session),
    manager = Depends(get_provider_manager)
) -> CompletionResponse:
    """
    OpenAI-compatible chat completion endpoint
    Routes to appropriate provider based on model
    """
    try:
        # Route to appropriate provider
        response = await manager.complete(request)

        # Log to database
        log_entry = Request(
            id=str(uuid.uuid4()),
            workflow_name="direct_completion",
            model=response.model,
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
