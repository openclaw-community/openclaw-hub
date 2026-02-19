"""
Provider manager for routing requests to appropriate providers
"""

from typing import Dict, Optional
from .base import ProviderBase, CompletionRequest, CompletionResponse
from .ollama import OllamaProvider
from .openai import OpenAIProvider
from .anthropic import AnthropicProvider
from .health import tracker as health_tracker
import structlog

logger = structlog.get_logger()


class ProviderManager:
    """Manages multiple LLM providers and routes requests"""

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        openai_api_key: Optional[str] = None,
        anthropic_api_key: Optional[str] = None
    ):
        self.providers: Dict[str, ProviderBase] = {}
        self.ollama_url = ollama_url

        # Always initialize Ollama (local, no API key)
        self.providers["ollama"] = OllamaProvider(base_url=ollama_url)

        # Initialize cloud providers if API keys provided
        if openai_api_key:
            self.providers["openai"] = OpenAIProvider(api_key=openai_api_key)

        if anthropic_api_key:
            self.providers["anthropic"] = AnthropicProvider(api_key=anthropic_api_key)

        logger.info(
            "provider_manager_initialized",
            providers=list(self.providers.keys())
        )

    def route_model(self, model: str) -> str:
        """Determine which provider to use for a given model"""
        model_lower = model.lower()

        # OpenAI models
        if any(x in model_lower for x in ["gpt-4", "gpt-3.5", "gpt-4o"]):
            return "openai"

        # Anthropic models
        if "claude" in model_lower:
            return "anthropic"

        # Default to Ollama for everything else
        return "ollama"

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Route completion request to appropriate provider"""
        provider_name = self.route_model(request.model)

        if provider_name not in self.providers:
            raise ValueError(
                f"Model '{request.model}' requires {provider_name} provider, "
                f"but API key not configured. Available providers: {list(self.providers.keys())}"
            )

        provider = self.providers[provider_name]

        logger.info(
            "routing_request",
            model=request.model,
            provider=provider_name
        )

        return await provider.complete(request)

    async def complete_with_provider(
        self, request: CompletionRequest, provider_name: str
    ) -> CompletionResponse:
        """
        Execute a completion against a specific named provider (bypasses model routing).
        Used by retry/fallback logic in completions.py.
        """
        if provider_name not in self.providers:
            raise ValueError(
                f"Provider '{provider_name}' not configured. "
                f"Available: {list(self.providers.keys())}"
            )
        return await self.providers[provider_name].complete(request)

    def get_probe_fn(self, provider_name: str):
        """
        Return a lightweight async probe function for the given provider.
        Probe functions raise an exception on failure.
        """
        provider = self.providers.get(provider_name)
        if provider is None:
            async def _missing(): raise ValueError(f"Provider {provider_name} not configured")
            return _missing

        if provider_name == "ollama":
            async def _probe_ollama():
                import httpx
                async with httpx.AsyncClient(timeout=10.0) as c:
                    r = await c.get(f"{self.ollama_url}/api/tags")
                    r.raise_for_status()
            return _probe_ollama

        if provider_name == "openai":
            async def _probe_openai():
                # Cheapest possible API call: just list models
                await provider.client.models.list()
            return _probe_openai

        if provider_name == "anthropic":
            async def _probe_anthropic():
                # Anthropic doesn't have a lightweight endpoint; use a minimal completion
                from anthropic import AsyncAnthropic
                client = AsyncAnthropic(api_key=provider.api_key)
                await client.messages.create(
                    model="claude-haiku-20240307",
                    max_tokens=1,
                    messages=[{"role": "user", "content": "ping"}]
                )
            return _probe_anthropic

        # Generic: no-op probe (just mark as healthy on next success)
        async def _noop(): pass
        return _noop

    async def list_all_models(self) -> Dict[str, list]:
        """List models from all providers"""
        all_models = {}

        for name, provider in self.providers.items():
            try:
                if name == "ollama":
                    models = await provider.list_models()
                else:
                    models = provider.list_models()
                all_models[name] = models
            except Exception as e:
                logger.error("failed_to_list_models", provider=name, error=str(e))
                all_models[name] = []

        return all_models

    async def close_all(self):
        """Close all provider connections"""
        for provider in self.providers.values():
            try:
                await provider.close()
            except Exception as e:
                logger.error("failed_to_close_provider", error=str(e))
