"""Image generation API endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Literal, Optional
import structlog

from ..images.generator import ImageGenerator

logger = structlog.get_logger()

router = APIRouter(prefix="/v1")

# Global generator instance
image_generator: Optional[ImageGenerator] = None


def get_generator() -> ImageGenerator:
    """Get or create the image generator instance."""
    global image_generator
    if image_generator is None:
        image_generator = ImageGenerator()
    return image_generator


class ImageGenerationRequest(BaseModel):
    """Request model for image generation."""
    prompt: str = Field(..., description="Text description of the desired image")
    model: Literal["dall-e-2", "dall-e-3"] = Field(
        default="dall-e-3",
        description="Model to use for generation"
    )
    size: Literal[
        "256x256", "512x512", "1024x1024",
        "1024x1792", "1792x1024"
    ] = Field(
        default="1024x1024",
        description="Image dimensions"
    )
    quality: Literal["standard", "hd"] = Field(
        default="standard",
        description="Image quality (DALL-E 3 only)"
    )
    n: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Number of images to generate"
    )
    response_format: Literal["url", "b64_json"] = Field(
        default="url",
        description="Response format"
    )


class ImageGenerationResponse(BaseModel):
    """Response model for image generation."""
    created: int
    data: list


@router.post("/images/generations", response_model=ImageGenerationResponse)
async def generate_image(request: ImageGenerationRequest):
    """
    Generate an image using OpenAI's DALL-E models.
    
    Compatible with OpenAI's image generation API format.
    """
    try:
        logger.info(
            "image_generation_request",
            model=request.model,
            size=request.size,
            quality=request.quality,
            n=request.n
        )
        
        generator = get_generator()
        
        result = await generator.generate(
            prompt=request.prompt,
            model=request.model,
            size=request.size,
            quality=request.quality,
            n=request.n,
            response_format=request.response_format
        )
        
        logger.info(
            "image_generation_success",
            model=request.model,
            images_generated=len(result["data"])
        )
        
        return result
        
    except ValueError as e:
        logger.error("image_generation_config_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("image_generation_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")
