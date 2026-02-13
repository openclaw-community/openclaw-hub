"""Video generation via OpenAI (Sora)."""
from typing import Optional
from openai import AsyncOpenAI
from ..config import settings
import structlog

logger = structlog.get_logger()


class VideoGenerator:
    """Generate videos using OpenAI's Sora models."""
    
    def __init__(self):
        api_key = settings.openai_api_key
        if not api_key:
            raise ValueError("OPENAI_API_KEY not configured")
        self.client = AsyncOpenAI(api_key=api_key)
    
    async def generate(
        self,
        prompt: str,
        model: str = "sora-2",
        duration: int = 5,
        resolution: str = "1080p",
        response_format: str = "url"
    ) -> dict:
        """
        Generate a video using Sora.
        
        Args:
            prompt: Text description of the video
            model: Model to use (sora-2, sora-2-pro)
            duration: Video duration in seconds (5, 10, or 20)
            resolution: Video resolution (720p, 1080p, 4k)
            response_format: url or b64_json
        
        Returns:
            OpenAI API response with video URL/data and metadata
        """
        # Note: Adjust this based on actual Sora API when available
        # This is based on expected OpenAI video generation API patterns
        
        params = {
            "model": model,
            "prompt": prompt,
            "duration": duration,
            "resolution": resolution,
            "response_format": response_format
        }
        
        logger.info(
            "video_generation_request",
            model=model,
            duration=duration,
            resolution=resolution
        )
        
        try:
            # Call OpenAI video generation API
            # Adjust endpoint based on actual API documentation
            response = await self.client.post(
                "/v1/videos/generations",
                json=params
            )
            
            result = {
                "created": response.get("created"),
                "data": response.get("data", []),
                "model": model,
                "duration": duration,
                "resolution": resolution
            }
            
            logger.info(
                "video_generation_success",
                model=model,
                duration=duration
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "video_generation_error",
                model=model,
                error=str(e)
            )
            raise
