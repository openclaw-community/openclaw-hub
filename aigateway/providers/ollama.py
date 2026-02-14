"""
Ollama provider implementation
"""

import httpx
import time
from typing import List
from .base import ProviderBase, CompletionRequest, CompletionResponse
import structlog

logger = structlog.get_logger()


class OllamaProvider(ProviderBase):
    """Provider for local Ollama models"""

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=120.0)

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Execute completion via Ollama API"""
        start_time = time.time()

        # Convert to OpenAI-compatible format
        ollama_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in request.messages
        ]

        # Translate "local" alias to actual model name
        model_name = request.model
        if model_name.lower() == "local":
            model_name = "qwen2.5:32b-instruct"

        payload = {
            "model": model_name,
            "messages": ollama_messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload
            )
            response.raise_for_status()
            result = response.json()

            latency_ms = int((time.time() - start_time) * 1000)

            # Extract from OpenAI-compatible format
            choice = result["choices"][0]
            usage = result.get("usage", {})
            
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", 0)

            return CompletionResponse(
                content=choice["message"]["content"],
                model=request.model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost_usd=0.0,  # Local model, no cost
                latency_ms=latency_ms
            )

        except httpx.HTTPError as e:
            logger.error("ollama_request_failed", error=str(e))
            raise

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int, model: str) -> float:
        """Ollama is free (local)"""
        return 0.0

    async def list_models(self) -> List[str]:
        """Fetch available Ollama models"""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            result = response.json()
            return [model["name"] for model in result.get("models", [])]
        except httpx.HTTPError as e:
            logger.error("ollama_list_models_failed", error=str(e))
            return []

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
