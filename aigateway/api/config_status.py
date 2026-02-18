"""Config status endpoint — shows which integrations are configured."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
import httpx
import structlog

from ..config import settings

logger = structlog.get_logger()

router = APIRouter(prefix="/v1")


def _is_set(value) -> bool:
    """Return True if a setting value is non-None and non-empty."""
    return bool(value and str(value).strip())


async def _github_login() -> str | None:
    """Fetch authenticated GitHub login. Returns None on failure."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"token {settings.github_token}",
                    "Accept": "application/vnd.github+json",
                },
            )
            if resp.status_code == 200:
                return resp.json().get("login")
    except Exception:
        pass
    return None


@router.get("/config/status", tags=["config"])
async def get_config_status():
    """
    Show which integrations are configured and ready.

    Returns configuration state for each integration without exposing
    raw API keys or secrets. Safe metadata (e.g. GitHub login, account IDs)
    is included where available.
    """
    # LLM providers
    llm = {
        "ollama": {
            "configured": True,  # always enabled — local
            "url": settings.ollama_url,
        },
        "openai": {
            "configured": _is_set(settings.openai_api_key),
        },
        "anthropic": {
            "configured": _is_set(settings.anthropic_api_key),
        },
    }

    # Social — Instagram via Late API
    instagram_configured = _is_set(settings.late_api_key)
    social = {
        "instagram": {
            "configured": instagram_configured,
            "provider": "late.dev",
            **(
                {"account_id": settings.late_instagram_account_id}
                if instagram_configured and _is_set(settings.late_instagram_account_id)
                else {}
            ),
        }
    }

    # GitHub
    github_configured = _is_set(settings.github_token)
    github_login = await _github_login() if github_configured else None
    github = {
        "configured": github_configured,
        **({"login": github_login} if github_login else {}),
    }

    # Image generation (DALL-E — requires OpenAI key)
    images = {
        "dalle": {
            "configured": _is_set(settings.openai_api_key),
            "models": ["dall-e-2", "dall-e-3"],
        }
    }

    # Video generation
    video = {
        "veo3": {
            "configured": _is_set(settings.openai_api_key),  # routed via OpenAI-compatible
            "models": ["veo3_fast", "veo3"],
        },
        "kling": {
            "configured": _is_set(settings.kie_api_key),
            "models": ["kling-2.6"],
        },
    }

    status = {
        "llm": llm,
        "social": social,
        "github": github,
        "images": images,
        "video": video,
    }

    logger.info("config_status_requested")
    return JSONResponse(status)
