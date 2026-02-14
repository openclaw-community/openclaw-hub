"""
Kie.ai provider for video generation via Kling 2.6 and VEO 3.1
"""

import httpx
import asyncio
import time
from typing import Optional, List
import structlog

logger = structlog.get_logger()


class KieProvider:
    """Provider for Kie.ai video generation (Kling 2.6 and VEO 3.1)"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.kie.ai"
        self.client = httpx.AsyncClient(timeout=300.0)  # 5 min timeout for video generation

    async def generate_video(
        self,
        prompt: str,
        duration: int = 5,
        aspect_ratio: str = "16:9",
        sound: bool = False,
        max_wait_seconds: int = 300
    ) -> dict:
        """
        Generate video using Kling 2.6
        
        Args:
            prompt: Text description of the video
            duration: Video duration in seconds (5, 10, or 20)
            aspect_ratio: Video aspect ratio (16:9, 9:16, 1:1)
            sound: Whether to generate audio
            max_wait_seconds: Maximum time to wait for generation
            
        Returns:
            dict with video_url, task_id, and metadata
        """
        start_time = time.time()
        
        # Create generation task
        create_payload = {
            "model": "kling-2.6/text-to-video",
            "input": {
                "prompt": prompt,
                "sound": sound,
                "aspect_ratio": aspect_ratio,
                "duration": str(duration)
            }
        }
        
        try:
            logger.info(
                "kie_video_generation_started",
                prompt=prompt[:100],
                duration=duration,
                aspect_ratio=aspect_ratio
            )
            
            # Submit task
            response = await self.client.post(
                f"{self.base_url}/api/v1/jobs/createTask",
                json=create_payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("code") != 200:
                raise Exception(f"Task creation failed: {result.get('msg', 'Unknown error')}")
            
            task_id = result["data"]["task_id"]
            logger.info("kie_task_created", task_id=task_id)
            
            # Poll for completion (Kie.ai uses async generation)
            video_url = await self._poll_task_status(task_id, max_wait_seconds)
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Calculate cost (Kling 2.6: $0.28 per 5s)
            cost_per_5s = 0.28
            cost_usd = (duration / 5.0) * cost_per_5s
            
            logger.info(
                "kie_video_generation_completed",
                task_id=task_id,
                duration=duration,
                cost_usd=cost_usd,
                latency_ms=latency_ms
            )
            
            return {
                "video_url": video_url,
                "task_id": task_id,
                "duration": duration,
                "aspect_ratio": aspect_ratio,
                "cost_usd": cost_usd,
                "latency_ms": latency_ms,
                "model": "kling-2.6",
                "provider": "kie.ai"
            }
            
        except httpx.HTTPError as e:
            logger.error("kie_request_failed", error=str(e))
            raise Exception(f"Kie.ai API request failed: {str(e)}")
        except Exception as e:
            logger.error("kie_video_generation_failed", error=str(e))
            raise

    async def _poll_task_status(self, task_id: str, max_wait_seconds: int) -> str:
        """
        Poll task status until completion or timeout
        
        Returns:
            str: Video URL when ready
        """
        start_time = time.time()
        poll_interval = 5  # Check every 5 seconds
        
        while (time.time() - start_time) < max_wait_seconds:
            try:
                response = await self.client.get(
                    f"{self.base_url}/api/v1/jobs/getTaskInfo",
                    params={"task_id": task_id},
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                response.raise_for_status()
                result = response.json()
                
                if result.get("code") != 200:
                    logger.warning("kie_task_status_check_failed", task_id=task_id, msg=result.get("msg"))
                    await asyncio.sleep(poll_interval)
                    continue
                
                status = result["data"].get("status")
                
                if status == "succeed":
                    video_url = result["data"]["output"]["video_url"]
                    logger.info("kie_task_completed", task_id=task_id, video_url=video_url)
                    return video_url
                    
                elif status == "failed":
                    error_msg = result["data"].get("error", "Unknown error")
                    raise Exception(f"Video generation failed: {error_msg}")
                    
                elif status in ["pending", "processing"]:
                    elapsed = int(time.time() - start_time)
                    logger.debug("kie_task_in_progress", task_id=task_id, status=status, elapsed_seconds=elapsed)
                    await asyncio.sleep(poll_interval)
                    
                else:
                    logger.warning("kie_unknown_status", task_id=task_id, status=status)
                    await asyncio.sleep(poll_interval)
                    
            except httpx.HTTPError as e:
                logger.warning("kie_status_check_error", task_id=task_id, error=str(e))
                await asyncio.sleep(poll_interval)
        
        # Timeout
        raise TimeoutError(f"Video generation timed out after {max_wait_seconds} seconds (task_id: {task_id})")

    async def generate_veo3_video(
        self,
        prompt: str,
        model: str = "veo3_fast",
        aspect_ratio: str = "16:9",
        image_urls: Optional[List[str]] = None,
        generation_type: Optional[str] = None,
        callback_url: Optional[str] = None,
        max_wait_seconds: int = 300
    ) -> dict:
        """
        Generate video using Google VEO 3.1
        
        Args:
            prompt: Text description of the video
            model: "veo3" (quality) or "veo3_fast" (cost-efficient)
            aspect_ratio: "16:9", "9:16", or "Auto"
            image_urls: Optional list of 1-2 image URLs for image-to-video
            generation_type: Optional, one of TEXT_2_VIDEO, FIRST_AND_LAST_FRAMES_2_VIDEO, REFERENCE_2_VIDEO
            callback_url: Optional webhook URL for async notifications
            max_wait_seconds: Maximum time to wait for generation
            
        Returns:
            dict with video_url, task_id, and metadata
        """
        start_time = time.time()
        
        # Build request payload
        payload = {
            "prompt": prompt,
            "model": model,
            "aspect_ratio": aspect_ratio,
            "enableTranslation": True
        }
        
        if image_urls:
            payload["imageUrls"] = image_urls
            
        if generation_type:
            payload["generationType"] = generation_type
            
        if callback_url:
            payload["callBackUrl"] = callback_url
        
        try:
            logger.info(
                "veo3_video_generation_started",
                prompt=prompt[:100],
                model=model,
                aspect_ratio=aspect_ratio,
                has_images=bool(image_urls)
            )
            
            # Submit task
            response = await self.client.post(
                f"{self.base_url}/api/v1/veo3/generate",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("code") != 200:
                error_msg = result.get("msg", "Unknown error")
                raise Exception(f"VEO 3.1 task creation failed: {error_msg}")
            
            task_id = result["data"]["task_id"]
            logger.info("veo3_task_created", task_id=task_id)
            
            # Poll for completion
            video_data = await self._poll_veo3_task_status(task_id, max_wait_seconds)
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Estimate cost (pricing varies by model and resolution)
            # VEO 3.1 Fast: ~$0.20/5s at 25% of Google pricing
            # VEO 3.1 Quality: ~$0.30/5s at 25% of Google pricing
            cost_usd = 0.20 if model == "veo3_fast" else 0.30
            
            logger.info(
                "veo3_video_generation_completed",
                task_id=task_id,
                model=model,
                cost_usd=cost_usd,
                latency_ms=latency_ms
            )
            
            return {
                "video_url": video_data["video_url"],
                "task_id": task_id,
                "model": model,
                "aspect_ratio": aspect_ratio,
                "duration": video_data.get("duration", 5),
                "resolution": video_data.get("resolution", "1080p"),
                "cost_usd": cost_usd,
                "latency_ms": latency_ms,
                "provider": "kie.ai/veo3"
            }
            
        except httpx.HTTPError as e:
            logger.error("veo3_request_failed", error=str(e))
            raise Exception(f"VEO 3.1 API request failed: {str(e)}")
        except Exception as e:
            logger.error("veo3_video_generation_failed", error=str(e))
            raise

    async def _poll_veo3_task_status(self, task_id: str, max_wait_seconds: int) -> dict:
        """
        Poll VEO 3.1 task status until completion or timeout
        
        Returns:
            dict with video_url and metadata
        """
        start_time = time.time()
        poll_interval = 5  # Check every 5 seconds
        
        while (time.time() - start_time) < max_wait_seconds:
            try:
                response = await self.client.get(
                    f"{self.base_url}/api/v1/veo3/query",
                    params={"task_id": task_id},
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                response.raise_for_status()
                result = response.json()
                
                if result.get("code") != 200:
                    logger.warning("veo3_task_status_check_failed", task_id=task_id, msg=result.get("msg"))
                    await asyncio.sleep(poll_interval)
                    continue
                
                data = result["data"]
                status = data.get("status")
                
                if status == "completed":
                    video_url = data.get("video_url") or data.get("videoUrl")
                    logger.info("veo3_task_completed", task_id=task_id, video_url=video_url)
                    return {
                        "video_url": video_url,
                        "duration": data.get("duration", 5),
                        "resolution": data.get("resolution", "1080p")
                    }
                    
                elif status == "failed":
                    error_msg = data.get("error", "Unknown error")
                    raise Exception(f"VEO 3.1 generation failed: {error_msg}")
                    
                elif status in ["pending", "processing", "queued"]:
                    elapsed = int(time.time() - start_time)
                    logger.debug("veo3_task_in_progress", task_id=task_id, status=status, elapsed_seconds=elapsed)
                    await asyncio.sleep(poll_interval)
                    
                else:
                    logger.warning("veo3_unknown_status", task_id=task_id, status=status)
                    await asyncio.sleep(poll_interval)
                    
            except httpx.HTTPError as e:
                logger.warning("veo3_status_check_error", task_id=task_id, error=str(e))
                await asyncio.sleep(poll_interval)
        
        # Timeout
        raise TimeoutError(f"VEO 3.1 generation timed out after {max_wait_seconds} seconds (task_id: {task_id})")

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
