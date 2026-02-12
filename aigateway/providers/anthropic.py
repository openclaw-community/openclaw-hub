"""
Anthropic provider implementation
"""

from anthropic import AsyncAnthropic
import time
from typing import List
from .base import ProviderBase, CompletionRequest, CompletionResponse
import structlog

logger = structlog.get_logger()


class AnthropicProvider(ProviderBase):
    """Provider for Anthropic Claude models"""

    # Pricing per 1M tokens (as of Feb 2024)
    PRICING = {
        "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
        "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.00},
        "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
        "claude-3-sonnet-20240229": {"input": 3.00, "output": 15.00},
        "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
    }

    # Model aliases for convenience
    ALIASES = {
        "claude-sonnet": "claude-3-5-sonnet-20241022",
        "claude-haiku": "claude-3-5-haiku-20241022",
        "claude-opus": "claude-3-opus-20240229",
    }

    def __init__(self, api_key: str):
        self.client = AsyncAnthropic(api_key=api_key)
        self.api_key = api_key

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Execute completion via Anthropic API"""
        start_time = time.time()

        # Resolve alias if needed
        model = self.ALIASES.get(request.model, request.model)

        # Convert to Anthropic format (system message separate)
        system_message = None
        messages = []
        
        for msg in request.messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                messages.append({"role": msg.role, "content": msg.content})

        try:
            response = await self.client.messages.create(
                model=model,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                system=system_message,
                messages=messages
            )

            latency_ms = int((time.time() - start_time) * 1000)

            # Extract usage from response
            prompt_tokens = response.usage.input_tokens
            completion_tokens = response.usage.output_tokens
            total_tokens = prompt_tokens + completion_tokens

            # Calculate cost
            cost = self.calculate_cost(prompt_tokens, completion_tokens, model)

            # Extract content (handle multiple content blocks)
            content = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    content += block.text

            return CompletionResponse(
                content=content,
                model=response.model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost_usd=cost,
                latency_ms=latency_ms
            )

        except Exception as e:
            logger.error("anthropic_request_failed", error=str(e), model=model)
            raise

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int, model: str) -> float:
        """Calculate cost based on Anthropic pricing"""
        if model not in self.PRICING:
            # Try to find base model without date suffix
            base_model = "-".join(model.split("-")[:-1])
            if base_model not in self.PRICING:
                logger.warning("unknown_model_pricing", model=model, using_default="claude-3-haiku-20240307")
                model = "claude-3-haiku-20240307"
        
        pricing = self.PRICING.get(model, self.PRICING["claude-3-haiku-20240307"])
        
        # Cost = (tokens / 1M) * price_per_1M
        input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
        output_cost = (completion_tokens / 1_000_000) * pricing["output"]
        
        return input_cost + output_cost

    def list_models(self) -> List[str]:
        """Return list of supported Anthropic models"""
        return list(self.PRICING.keys()) + list(self.ALIASES.keys())

    async def close(self):
        """Close HTTP client"""
        await self.client.close()
