"""
OpenAI provider implementation
"""

from openai import AsyncOpenAI
import time
from typing import List
from .base import ProviderBase, CompletionRequest, CompletionResponse
import structlog

logger = structlog.get_logger()


class OpenAIProvider(ProviderBase):
    """Provider for OpenAI models (GPT-4, GPT-3.5, etc.)"""

    # Pricing per 1M tokens (as of Feb 2024)
    PRICING = {
        "gpt-4-turbo": {"input": 10.00, "output": 30.00},
        "gpt-4": {"input": 30.00, "output": 60.00},
        "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    }

    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)
        self.api_key = api_key

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Execute completion via OpenAI API"""
        start_time = time.time()

        # Convert to OpenAI format
        openai_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in request.messages
        ]

        try:
            response = await self.client.chat.completions.create(
                model=request.model,
                messages=openai_messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                stream=False
            )

            latency_ms = int((time.time() - start_time) * 1000)

            # Extract usage from response
            usage = response.usage
            prompt_tokens = usage.prompt_tokens
            completion_tokens = usage.completion_tokens
            total_tokens = usage.total_tokens

            # Calculate cost
            cost = self.calculate_cost(prompt_tokens, completion_tokens, request.model)

            return CompletionResponse(
                content=response.choices[0].message.content,
                model=response.model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost_usd=cost,
                latency_ms=latency_ms
            )

        except Exception as e:
            logger.error("openai_request_failed", error=str(e), model=request.model)
            raise

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int, model: str) -> float:
        """Calculate cost based on OpenAI pricing"""
        # Normalize model name (handle versioned models)
        base_model = model.split("-20")[0]  # Remove date suffix if present
        
        if base_model not in self.PRICING:
            # Default to gpt-3.5-turbo pricing for unknown models
            logger.warning("unknown_model_pricing", model=model, using_default="gpt-3.5-turbo")
            base_model = "gpt-3.5-turbo"
        
        pricing = self.PRICING[base_model]
        
        # Cost = (tokens / 1M) * price_per_1M
        input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
        output_cost = (completion_tokens / 1_000_000) * pricing["output"]
        
        return input_cost + output_cost

    def list_models(self) -> List[str]:
        """Return list of supported OpenAI models"""
        return list(self.PRICING.keys())

    async def close(self):
        """Close HTTP client"""
        await self.client.close()
