"""
Kie.ai provider for video generation via Kling 2.6 and VEO 3.1
"""

import httpx
import asyncio
import time
from typing import Optional
import structlog

logger = structlog.get_logger()


class KieProvider:
    """Provider for Kie.ai video generation (Kling 2.6 and VEO 3.1)"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.kie.ai"
        self.client = httpx.AsyncClient(timeout=600.0)
        self.logger = structlog.get_logger().bind(provider="kie.ai")

    async def generate_video(
        self,
        prompt: str,
        duration: int = 5,
        aspect_ratio: str = "16:9",
        sound: bool = False,
        model: Optional[str] = "veo3",
        max_wait_seconds: int = 600
    ) -> dict:
        """
        Generate video using Kie.ai (Kling 2.6 or VEO 3.1).

        Args:
            prompt: Text description of the video
            duration: Video duration in seconds
            aspect_ratio: Video aspect ratio (16:9, 9:16, 1:1, Auto)
            sound: Whether to generate audio
            model: Model to use (kling-2.6, veo3_fast, veo3)
            max_wait_seconds: Maximum time to wait for generation

        Returns:
            dict with video_url, task_id, and metadata
        """
        start_time = time.time()
        is_kling = model and model.startswith("kling")

        if is_kling:
            create_payload = {
                "model": "kling-2.6/text-to-video",
                "input": {
                    "prompt": prompt,
                    "sound": sound,
                    "aspect_ratio": aspect_ratio,
                    "duration": str(duration)
                }
            }
            endpoint = f"{self.base_url}/api/v1/jobs/createTask"
            cost_per_5s = 0.28
            provider_name = "kling-2.6"
        else:
            create_payload = {
                "model": model,
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "enableTranslation": True
            }
            if duration in [4, 6, 8]:
                create_payload["duration"] = str(duration)
            if sound:
                create_payload["sound"] = sound
            endpoint = f"{self.base_url}/api/v1/veo/generate"
            cost_per_5s = 0.20 if model == "veo3_fast" else 0.30
            provider_name = "veo3"

        try:
            self.logger.info(
                "video_generation_started",
                prompt=prompt[:250],
                model=model,
                duration=duration,
                aspect_ratio=aspect_ratio
            )

            # Submit task
            response = await self.client.post(
                endpoint,
                json=create_payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )
            response.raise_for_status()
            result = response.json()

            if result.get("code") != 200:
                error_msg = result.get("msg", "Unknown error")
                raise Exception(f"Task creation failed: {error_msg}")

            data = result.get("data") or {}
            task_id = data.get("taskId") or data.get("task_id") or data.get("id")
            if not task_id:
                self.logger.error("no_task_id", full_result=result)
                raise Exception("No task ID found in API response")

            self.logger.info("task_created", task_id=task_id, model=model)

            # Poll for completion
            if is_kling:
                video_url = await self._poll_kling_task(task_id, max_wait_seconds)
                video_data = {"video_url": video_url, "duration": duration, "resolution": "1080p"}
            else:
                video_data = await self._poll_veo3_task(task_id, max_wait_seconds)

            latency_ms = int((time.time() - start_time) * 1000)
            cost_usd = (duration / 5.0) * cost_per_5s

            self.logger.info(
                "video_generation_completed",
                task_id=task_id,
                model=model,
                cost_usd=cost_usd,
                latency_ms=latency_ms
            )

            return {
                "video_url": video_data["video_url"],
                "task_id": task_id,
                "duration": video_data.get("duration", duration),
                "aspect_ratio": aspect_ratio,
                "resolution": video_data.get("resolution", "1080p"),
                "cost_usd": cost_usd,
                "latency_ms": latency_ms,
                "model": model,
                "provider": f"kie.ai/{provider_name}"
            }

        except httpx.HTTPError as e:
            self.logger.error("request_failed", error=str(e))
            raise Exception(f"Kie.ai API request failed: {str(e)}")
        except Exception as e:
            self.logger.error("video_generation_failed", error=str(e))
            raise

    async def _poll_kling_task(self, task_id: str, max_wait_seconds: int) -> str:
        """Poll Kling task status. Returns video URL."""
        start_time = time.time()
        poll_interval = 5

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
                    self.logger.warning("kling_status_check_failed", task_id=task_id, msg=result.get("msg"))
                    await asyncio.sleep(poll_interval)
                    continue

                data = result.get("data") or {}
                status = data.get("status")

                if status == "succeed":
                    output = data.get("output") or {}
                    video_url = output.get("video_url")
                    self.logger.info("kling_task_completed", task_id=task_id)
                    return video_url
                elif status == "failed":
                    error_msg = data.get("error", "Unknown error")
                    raise Exception(f"Kling generation failed: {error_msg}")
                else:
                    elapsed = int(time.time() - start_time)
                    self.logger.debug("kling_in_progress", task_id=task_id, status=status, elapsed=elapsed)
                    await asyncio.sleep(poll_interval)

            except httpx.HTTPError as e:
                self.logger.warning("kling_status_error", task_id=task_id, error=str(e))
                await asyncio.sleep(poll_interval)

        raise TimeoutError(f"Kling generation timed out after {max_wait_seconds}s (task_id: {task_id})")

    async def _poll_veo3_task(self, task_id: str, max_wait_seconds: int) -> dict:
        """Poll VEO 3.1 task status. Returns dict with video_url and metadata."""
        start_time = time.time()
        poll_interval = 5

        self.logger.info("veo3_polling_started", task_id=task_id, max_wait=max_wait_seconds)

        while (time.time() - start_time) < max_wait_seconds:
            elapsed = int(time.time() - start_time)

            try:
                response = await self.client.get(
                    f"{self.base_url}/api/v1/veo/record-info",
                    params={"taskId": task_id},
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                response.raise_for_status()
                result = response.json()

                if result.get("code") != 200:
                    self.logger.warning("veo3_status_check_failed", task_id=task_id, msg=result.get("msg"), elapsed=elapsed)
                    await asyncio.sleep(poll_interval)
                    continue

                data = result.get("data") or {}
                success_flag = data.get("successFlag")

                if success_flag == 1:  # Success
                    response_data = data.get("response") or {}
                    # API returns resultUrls array; fall back to videoUrl/video_url
                    result_urls = response_data.get("resultUrls") or []
                    video_url = (
                        (result_urls[0] if result_urls else None) or
                        response_data.get("videoUrl") or
                        response_data.get("video_url")
                    )
                    resolution = response_data.get("resolution", "1080p")
                    self.logger.info("veo3_completed", task_id=task_id, elapsed=elapsed, video_url=video_url)
                    return {
                        "video_url": video_url,
                        "duration": response_data.get("duration", 8),
                        "resolution": resolution
                    }
                elif success_flag in [2, 3]:  # Failed
                    error_msg = data.get("error", "Generation failed")
                    raise Exception(f"VEO 3.1 generation failed: {error_msg}")
                elif success_flag == 0:  # In progress
                    self.logger.debug("veo3_in_progress", task_id=task_id, elapsed=elapsed)
                    await asyncio.sleep(poll_interval)
                else:
                    self.logger.warning("veo3_unknown_status", task_id=task_id, flag=success_flag, elapsed=elapsed)
                    await asyncio.sleep(poll_interval)

            except httpx.HTTPError as e:
                self.logger.warning("veo3_status_error", task_id=task_id, error=str(e), elapsed=elapsed)
                await asyncio.sleep(poll_interval)

        raise TimeoutError(f"VEO 3.1 generation timed out after {max_wait_seconds}s (task_id: {task_id})")

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
