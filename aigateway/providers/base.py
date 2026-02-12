"""
Base provider interface for LLM abstraction
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from pydantic import BaseModel


class Message(BaseModel):
    """Standard message format"""
    role: str  # "user", "assistant", "system"
    content: str


class CompletionRequest(BaseModel):
    """Standard completion request"""
    messages: List[Message]
    model: str
    max_tokens: int = 1000
    temperature: float = 0.7
    stream: bool = False


class CompletionResponse(BaseModel):
    """Standard completion response"""
    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    latency_ms: int


class ProviderBase(ABC):
    """Base class for LLM providers"""

    @abstractmethod
    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """
        Execute a completion request
        
        Args:
            request: Standardized completion request
            
        Returns:
            Standardized completion response
        """
        pass

    @abstractmethod
    def calculate_cost(self, prompt_tokens: int, completion_tokens: int, model: str) -> float:
        """
        Calculate cost in USD for token usage
        
        Args:
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
            model: Model identifier
            
        Returns:
            Cost in USD
        """
        pass

    @abstractmethod
    def list_models(self) -> List[str]:
        """Return list of available models for this provider"""
        pass
