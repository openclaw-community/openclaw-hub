"""Social media posting API endpoints."""
from fastapi import APIRouter, HTTPException, File, UploadFile
from pydantic import BaseModel, Field
from typing import Optional, List
import structlog
import os
import tempfile

from ..social.late import LateClient

logger = structlog.get_logger()

router = APIRouter(prefix="/v1")

# Global client instance
late_client: Optional[LateClient] = None


def get_late_client() -> LateClient:
    """Get or create the Late client instance."""
    global late_client
    if late_client is None:
        late_client = LateClient()
    return late_client


class InstagramPostRequest(BaseModel):
    """Request model for Instagram posting."""
    account_id: str = Field(..., description="Late Instagram account ID")
    caption: str = Field(..., description="Post caption text")
    media_urls: List[str] = Field(..., description="List of public media URLs")
    media_type: str = Field(default="image", description="Media type (image or video)")
    publish_now: bool = Field(default=True, description="Post immediately or schedule")
    scheduled_for: Optional[str] = Field(None, description="ISO timestamp for scheduled posts")


class InstagramPostResponse(BaseModel):
    """Response model for Instagram posting."""
    success: bool
    post_id: Optional[str]
    instagram_url: Optional[str]
    message: str


@router.post("/social/instagram/post", response_model=InstagramPostResponse)
async def post_to_instagram(request: InstagramPostRequest):
    """
    Post to Instagram via Late API.
    
    Supports single images, carousels (multiple images), and videos.
    """
    try:
        logger.info(
            "instagram_post_request",
            account_id=request.account_id,
            media_count=len(request.media_urls),
            media_type=request.media_type
        )
        
        client = get_late_client()
        
        result = await client.post_to_instagram(
            account_id=request.account_id,
            caption=request.caption,
            media_urls=request.media_urls,
            media_type=request.media_type,
            publish_now=request.publish_now,
            scheduled_for=request.scheduled_for
        )
        
        post_id = result.get("post", {}).get("_id")
        ig_url = result.get("post", {}).get("platforms", [{}])[0].get("platformPostUrl")
        
        return InstagramPostResponse(
            success=True,
            post_id=post_id,
            instagram_url=ig_url,
            message="Post published successfully"
        )
        
    except ValueError as e:
        logger.error("instagram_post_config_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("instagram_post_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to post to Instagram: {str(e)}")


@router.post("/social/instagram/upload")
async def upload_instagram_media(file: UploadFile = File(...)):
    """
    Upload media for Instagram posting.
    
    Returns public URL that can be used in post request.
    """
    try:
        client = get_late_client()
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            # Determine content type
            content_type = file.content_type or "image/png"
            
            # Upload to Late
            public_url = await client.upload_media(tmp_path, content_type)
            
            logger.info("media_upload_success", filename=file.filename, url=public_url)
            
            return {
                "success": True,
                "url": public_url,
                "filename": file.filename
            }
        finally:
            # Clean up temp file
            os.unlink(tmp_path)
            
    except Exception as e:
        logger.error("media_upload_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to upload media: {str(e)}")


@router.get("/social/capabilities")
async def get_social_capabilities():
    """List available social media capabilities."""
    return {
        "platforms": {
            "instagram": {
                "provider": "late.dev",
                "capabilities": [
                    "post_image",
                    "post_carousel",
                    "post_video",
                    "schedule_post",
                    "upload_media"
                ],
                "endpoints": {
                    "post": "/v1/social/instagram/post",
                    "upload": "/v1/social/instagram/upload"
                },
                "media_types": ["image/png", "image/jpeg", "video/mp4"],
                "max_carousel_items": 10
            }
        }
    }
