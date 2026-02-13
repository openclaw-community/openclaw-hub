"""Image generation via OpenAI (DALL-E, Sora)."""
from typing import Optional
from openai import AsyncOpenAI
from ..config import settings


class ImageGenerator:
    """Generate images using OpenAI's image generation APIs."""
    
    def __init__(self):
        api_key = settings.openai_api_key
        if not api_key:
            raise ValueError("OPENAI_API_KEY not configured")
        self.client = AsyncOpenAI(api_key=api_key)
    
    async def generate(
        self,
        prompt: str,
        model: str = "dall-e-3",
        size: str = "1024x1024",
        quality: str = "standard",
        n: int = 1,
        response_format: str = "url"
    ) -> dict:
        """
        Generate an image.
        
        Args:
            prompt: Text description of the image
            model: Model to use (dall-e-2, dall-e-3)
            size: Image size (256x256, 512x512, 1024x1024, 1024x1792, 1792x1024)
            quality: Quality level (standard, hd) - DALL-E 3 only
            n: Number of images (1-10 for DALL-E 2, must be 1 for DALL-E 3)
            response_format: url or b64_json
        
        Returns:
            OpenAI API response with image URLs/data
        """
        params = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "n": n,
            "response_format": response_format
        }
        
        # Quality parameter only for DALL-E 3
        if model == "dall-e-3":
            params["quality"] = quality
        
        response = await self.client.images.generate(**params)
        
        return {
            "created": response.created,
            "data": [
                {
                    "url": img.url if hasattr(img, "url") else None,
                    "b64_json": img.b64_json if hasattr(img, "b64_json") else None,
                    "revised_prompt": img.revised_prompt if hasattr(img, "revised_prompt") else None
                }
                for img in response.data
            ]
        }
