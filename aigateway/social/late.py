"""Late API client for Instagram posting via getlate.dev."""
from typing import Optional, List, Dict, Any
import httpx
import structlog
from ..config import settings

logger = structlog.get_logger()


class LateClient:
    """Client for Late API (Instagram posting service)."""
    
    def __init__(self):
        self.api_key = settings.late_api_key
        if not self.api_key:
            raise ValueError("LATE_API_KEY not configured")
        
        self.base_url = "https://getlate.dev/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def get_presigned_url(
        self,
        filename: str,
        content_type: str = "image/png"
    ) -> Dict[str, str]:
        """Get presigned URL for media upload.
        
        Args:
            filename: Name of the file
            content_type: MIME type (image/png, image/jpeg, video/mp4, etc.)
        
        Returns:
            Dict with uploadUrl, publicUrl, key, expiresIn
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/media/presign",
                headers=self.headers,
                json={
                    "filename": filename,
                    "contentType": content_type
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def upload_media(
        self,
        file_path: str,
        content_type: str = "image/png"
    ) -> str:
        """Upload media file and return public URL.
        
        Args:
            file_path: Path to local file
            content_type: MIME type
        
        Returns:
            Public URL of uploaded media
        """
        import os
        filename = os.path.basename(file_path)
        
        # Get presigned URL
        presign_data = await self.get_presigned_url(filename, content_type)
        upload_url = presign_data["uploadUrl"]
        public_url = presign_data["publicUrl"]
        
        # Upload file
        with open(file_path, "rb") as f:
            file_data = f.read()
        
        async with httpx.AsyncClient() as client:
            response = await client.put(
                upload_url,
                content=file_data,
                headers={"Content-Type": content_type}
            )
            response.raise_for_status()
        
        logger.info("media_uploaded", filename=filename, url=public_url)
        return public_url
    
    async def post_to_instagram(
        self,
        account_id: str,
        caption: str,
        media_urls: List[str],
        media_type: str = "image",
        publish_now: bool = True,
        scheduled_for: Optional[str] = None
    ) -> Dict[str, Any]:
        """Post to Instagram via Late API.
        
        Args:
            account_id: Late Instagram account ID
            caption: Post caption text
            media_urls: List of public media URLs (for carousel, provide multiple)
            media_type: "image" or "video"
            publish_now: If True, post immediately; if False, schedule
            scheduled_for: ISO timestamp for scheduled posts
        
        Returns:
            Post response with ID, URL, and status
        """
        media_items = [
            {"url": url, "type": media_type}
            for url in media_urls
        ]
        
        payload = {
            "content": caption,
            "platforms": [{
                "platform": "instagram",
                "accountId": account_id
            }],
            "mediaItems": media_items,
            "publishNow": publish_now
        }
        
        if scheduled_for and not publish_now:
            payload["scheduledFor"] = scheduled_for
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/posts",
                headers=self.headers,
                json=payload,
                timeout=60.0
            )
            response.raise_for_status()
            result = response.json()
        
        post_id = result.get("post", {}).get("_id")
        ig_url = result.get("post", {}).get("platforms", [{}])[0].get("platformPostUrl")
        
        logger.info(
            "instagram_post_created",
            post_id=post_id,
            url=ig_url,
            media_count=len(media_urls)
        )
        
        return result
