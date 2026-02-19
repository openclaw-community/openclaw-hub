"""Late API client for Instagram posting via getlate.dev."""
import time
import json
from typing import Optional, List, Dict, Any
import httpx
import structlog
from ..config import settings
from ..dashboard.api_logger import log_api_call

logger = structlog.get_logger()


class LateClient:
    """Client for Late API (Instagram posting service)."""

    def __init__(self):
        # The Connections UI writes GETLATE_API_KEY; legacy env var is LATE_API_KEY.
        # Prefer GETLATE_API_KEY if present.
        self.api_key = settings.getlate_api_key or settings.late_api_key
        if not self.api_key:
            raise ValueError("GETLATE_API_KEY (or LATE_API_KEY) not configured")

        self.base_url = "https://getlate.dev/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        path: str,
        operation: str,
        payload: Optional[Dict] = None,
        timeout: float = 60.0,
    ) -> Any:
        """
        Make an instrumented HTTP request to the Late API.

        Measures latency, logs the result to api_calls regardless of
        success or failure, then re-raises any exception.
        """
        url = f"{self.base_url}{path}"
        start = time.monotonic()
        status_code: Optional[int] = None
        success = True
        error_msg: Optional[str] = None
        request_bytes: Optional[int] = None
        response_bytes: Optional[int] = None

        try:
            kwargs: Dict = {"headers": self.headers, "timeout": timeout}
            if payload is not None:
                kwargs["json"] = payload
                request_bytes = len(json.dumps(payload).encode())

            async with httpx.AsyncClient() as client:
                response = await client.request(method, url, **kwargs)
                status_code = response.status_code
                response_bytes = len(response.content)
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            success = False
            error_msg = exc.response.text[:500]
            raise

        except Exception as exc:
            success = False
            error_msg = str(exc)
            raise

        finally:
            latency = (time.monotonic() - start) * 1000
            await log_api_call(
                service="late",
                operation=operation,
                endpoint=path,
                method=method.upper(),
                status_code=status_code,
                success=success,
                error=error_msg,
                latency_ms=latency,
                request_size_bytes=request_bytes,
                response_size_bytes=response_bytes,
            )

    async def get_presigned_url(
        self,
        filename: str,
        content_type: str = "image/png",
    ) -> Dict[str, str]:
        """Get presigned URL for media upload."""
        return await self._request(
            "POST",
            "/media/presign",
            operation="get_presigned_url",
            payload={"filename": filename, "contentType": content_type},
        )

    async def upload_media(self, file_path: str, content_type: str = "image/png") -> str:
        """
        Upload media file and return public URL.

        Step 1: get_presigned_url (logged as service=late, op=get_presigned_url)
        Step 2: PUT to S3 presigned URL (logged as service=s3, op=upload_media)
        """
        import os
        filename = os.path.basename(file_path)

        # Step 1 — get presigned URL (instrumented inside get_presigned_url)
        presign_data = await self.get_presigned_url(filename, content_type)
        upload_url = presign_data["uploadUrl"]
        public_url = presign_data["publicUrl"]

        # Step 2 — upload to S3 (direct PUT, log separately)
        with open(file_path, "rb") as f:
            file_data = f.read()

        start = time.monotonic()
        status_code: Optional[int] = None
        success = True
        error_msg: Optional[str] = None

        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    upload_url,
                    content=file_data,
                    headers={"Content-Type": content_type},
                )
                status_code = response.status_code
                response.raise_for_status()

        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            success = False
            error_msg = exc.response.text[:500]
            raise

        except Exception as exc:
            success = False
            error_msg = str(exc)
            raise

        finally:
            latency = (time.monotonic() - start) * 1000
            await log_api_call(
                service="s3",
                operation="upload_media",
                endpoint=upload_url.split("?")[0],   # strip query params (presign creds)
                method="PUT",
                status_code=status_code,
                success=success,
                error=error_msg,
                latency_ms=latency,
                request_size_bytes=len(file_data),
                metadata={"filename": filename, "content_type": content_type},
            )

        logger.info("media_uploaded", filename=filename, url=public_url)
        return public_url

    async def post_to_instagram(
        self,
        account_id: str,
        caption: str,
        media_urls: List[str],
        media_type: str = "image",
        publish_now: bool = True,
        scheduled_for: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Post to Instagram via Late API."""
        media_items = [{"url": url, "type": media_type} for url in media_urls]

        payload: Dict[str, Any] = {
            "content": caption,
            "platforms": [{"platform": "instagram", "accountId": account_id}],
            "mediaItems": media_items,
            "publishNow": publish_now,
        }
        if scheduled_for and not publish_now:
            payload["scheduledFor"] = scheduled_for

        result = await self._request(
            "POST",
            "/posts",
            operation="post_to_instagram",
            payload=payload,
        )

        post_id = result.get("post", {}).get("_id")
        ig_url = result.get("post", {}).get("platforms", [{}])[0].get("platformPostUrl")

        logger.info(
            "instagram_post_created",
            post_id=post_id,
            url=ig_url,
            media_count=len(media_urls),
        )
        return result
