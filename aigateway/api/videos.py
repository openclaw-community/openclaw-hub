"""Video generation API endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Literal, Optional
import structlog
import time
from ..config import settings

logger = structlog.get_logger()

router = APIRouter(prefix="/v1")


class VideoGenerationRequest(BaseModel):
    """Request model for video generation."""
    prompt: str = Field(..., description="Text description of the desired video")
    model: Literal["sora-2", "sora-2-pro", "kling-2.6", "veo3", "veo3_fast"] = Field(
        default="veo3",
        description="Model to use for generation"
    )
    duration: Literal[5, 10, 20] = Field(
        default=5,
        description="Video duration in seconds (Kling only)"
    )
    resolution: Literal["720p", "1080p", "4k"] = Field(
        default="1080p",
        description="Video resolution"
    )
    aspect_ratio: Optional[Literal["16:9", "9:16", "1:1", "Auto"]] = Field(
        default=None,
        description="Video aspect ratio"
    )
    sound: bool = Field(
        default=False,
        description="Generate audio/sound effects (Kling only, VEO includes audio by default)"
    )
    image_urls: Optional[list[str]] = Field(
        default=None,
        description="Image URLs for image-to-video (VEO 3.1: 1-2 images)"
    )
    response_format: Literal["url", "b64_json"] = Field(
        default="url",
        description="Response format"
    )


class VideoGenerationResponse(BaseModel):
    """Response model for video generation."""
    created: int
    model: str
    duration: int
    resolution: str
    data: list


@router.post("/videos/generations", response_model=VideoGenerationResponse)
async def generate_video(request: VideoGenerationRequest):
    """
    Generate a video using AI models (VEO 3.1, Kling 2.6, Sora).
    
    **Available Models:**
    - veo3_fast: Google VEO 3.1 Fast (recommended, ~$0.20/5s, includes audio)
    - veo3: Google VEO 3.1 Quality (~$0.30/5s, highest fidelity, includes audio)
    - kling-2.6: Kling AI via Kie.ai ($0.28/5s, optional audio)
    - sora-2, sora-2-pro: Awaiting OpenAI API access
    
    **VEO 3.1 Features:**
    - Native vertical video (true 9:16 support)
    - Multilingual prompts
    - Text-to-video and image-to-video
    - 1080p default, 4K available
    - Background audio included
    - 25% of Google's direct pricing
    """
    try:
        logger.info(
            "video_generation_request",
            model=request.model,
            duration=request.duration,
            prompt=request.prompt[:100]
        )
        
        # VEO 3.1 via Kie.ai (recommended)
        if request.model in ["veo3", "veo3_fast"]:
            if not settings.kie_api_key:
                raise HTTPException(
                    status_code=500,
                    detail="KIE_API_KEY not configured"
                )
            
            from ..providers.kie import KieProvider
            kie = KieProvider(api_key=settings.kie_api_key)
            
            aspect_ratio = request.aspect_ratio or "16:9"
            
            try:
                result = await kie.generate_video(
                    prompt=request.prompt,
                    model=request.model,
                    aspect_ratio=aspect_ratio,
                    duration=5,  # default duration
                    max_wait_seconds=300
                )
                
                return VideoGenerationResponse(
                    created=int(time.time()),
                    model=result["model"],
                    duration=result["duration"],
                    resolution=result["resolution"],
                    data=[{
                        "url": result["video_url"],
                        "task_id": result["task_id"],
                        "cost_usd": result["cost_usd"],
                        "latency_ms": result["latency_ms"],
                        "provider": result["provider"],
                        "aspect_ratio": result["aspect_ratio"]
                    }]
                )
            finally:
                await kie.close()
        
        # Kling 2.6 via Kie.ai
        elif request.model == "kling-2.6":
            if not settings.kie_api_key:
                raise HTTPException(
                    status_code=500,
                    detail="KIE_API_KEY not configured"
                )
            
            from ..providers.kie import KieProvider
            kie = KieProvider(api_key=settings.kie_api_key)
            
            # Map resolution to aspect ratio (if not explicitly provided)
            aspect_ratio = request.aspect_ratio or "16:9"
            
            try:
                result = await kie.generate_video(
                    prompt=request.prompt,
                    duration=request.duration,
                    aspect_ratio=aspect_ratio,
                    sound=request.sound,
                    max_wait_seconds=300
                )
                
                return VideoGenerationResponse(
                    created=int(time.time()),
                    model="kling-2.6",
                    duration=request.duration,
                    resolution=f"{aspect_ratio} (aspect ratio)",
                    data=[{
                        "url": result["video_url"],
                        "task_id": result["task_id"],
                        "cost_usd": result["cost_usd"],
                        "latency_ms": result["latency_ms"],
                        "provider": "kie.ai"
                    }]
                )
            finally:
                await kie.close()
        
        # Sora models (not yet available)
        elif request.model in ["sora-2", "sora-2-pro"]:
            raise HTTPException(
                status_code=501,
                detail={
                    "error": "Sora API not available",
                    "message": "OpenAI Sora API access required. Use model='kling-2.6' for production video generation.",
                    "available_models": ["kling-2.6"],
                    "request_received": {
                        "model": request.model,
                        "duration": request.duration,
                        "prompt": request.prompt[:100]
                    }
                }
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("video_generation_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Video generation failed: {str(e)}"
        )


@router.get("/videos/capabilities")
async def get_video_capabilities():
    """List video generation capabilities."""
    kie_configured = bool(settings.kie_api_key)
    
    return {
        "status": "production_ready" if kie_configured else "limited",
        "message": "VEO 3.1 and Kling 2.6 available via Kie.ai. Sora integration pending.",
        "models": {
            "veo3_fast": {
                "description": "Google VEO 3.1 Fast - Cost-efficient, high-quality video (RECOMMENDED)",
                "provider": "kie.ai/veo3",
                "aspect_ratio_options": ["16:9", "9:16", "Auto"],
                "resolution_options": ["1080p", "4k (separate endpoint)"],
                "features": [
                    "text-to-video",
                    "image-to-video (1-2 images)",
                    "native vertical video",
                    "multilingual prompts",
                    "includes audio"
                ],
                "cost": "~$0.20 per 5s (25% of Google direct pricing)",
                "status": "available" if kie_configured else "not_configured"
            },
            "veo3": {
                "description": "Google VEO 3.1 Quality - Highest fidelity video generation",
                "provider": "kie.ai/veo3",
                "aspect_ratio_options": ["16:9", "9:16", "Auto"],
                "resolution_options": ["1080p", "4k (separate endpoint)"],
                "features": [
                    "text-to-video",
                    "image-to-video (1-2 images)",
                    "native vertical video",
                    "multilingual prompts",
                    "includes audio"
                ],
                "cost": "~$0.30 per 5s (25% of Google direct pricing)",
                "status": "available" if kie_configured else "not_configured"
            },
            "kling-2.6": {
                "description": "Kling AI 2.6 - Alternative video generation",
                "provider": "kie.ai",
                "duration_options": [5, 10, 20],
                "aspect_ratio_options": ["16:9", "9:16", "1:1"],
                "features": ["text-to-video", "natural motion", "optional audio"],
                "cost": "$0.28 per 5 seconds",
                "status": "available" if kie_configured else "not_configured"
            },
            "sora-2": {
                "description": "Cost-optimized video generation (OpenAI)",
                "duration_options": [5, 10, 20],
                "resolution_options": ["720p", "1080p", "4k"],
                "estimated_cost": "$0.80 per 5 seconds (pricing TBD)",
                "status": "api_pending"
            },
            "sora-2-pro": {
                "description": "Quality-optimized video generation (OpenAI)",
                "duration_options": [5, 10, 20],
                "resolution_options": ["720p", "1080p", "4k"],
                "estimated_cost": "$0.80+ per 5 seconds",
                "status": "api_pending"
            }
        },
        "endpoint": "/v1/videos/generations",
        "recommended_model": "veo3",
        "example": {
            "prompt": "A robot crab with glowing cyan eyes walking on a sandy beach at sunset, waves gently washing ashore",
            "model": "veo3_fast",
            "aspect_ratio": "16:9"
        },
        "docs": "VEO 3.1 recommended for production (cost-effective, includes audio). Kling 2.6 available as alternative. Sora integration pending OpenAI API access."
    }
