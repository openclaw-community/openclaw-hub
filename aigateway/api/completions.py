"""
Completion API endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ..providers.base import CompletionRequest, CompletionResponse
from ..providers.ollama import OllamaProvider
from ..storage.database import get_session
from ..storage.models import Request
import uuid
import structlog

logger = structlog.get_logger()
router = APIRouter()

# Initialize provider (will be moved to dependency injection later)
ollama = OllamaProvider()


@router.post("/v1/chat/completions", response_model=CompletionResponse)
async def create_completion(
    request: CompletionRequest,
    db: AsyncSession = Depends(get_session)
) -> CompletionResponse:
    """
    OpenAI-compatible chat completion endpoint
    Routes to appropriate provider based on model
    """
    try:
        # For MVP, route to Ollama for all requests
        # TODO: Smart routing based on model prefix
        response = await ollama.complete(request)

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
            latency_ms=response.latency_ms
        )

        return response

    except Exception as e:
        logger.error("completion_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v1/models")
async def list_models():
    """List available models"""
    models = await ollama.list_models()
    return {"models": models}
