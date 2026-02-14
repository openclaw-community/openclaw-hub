"""
Configuration management for AI Gateway
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Server
    host: str = "127.0.0.1"
    port: int = 8080
    reload: bool = False
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./aigateway.db"
    
    # Ollama (local)
    ollama_url: str = "http://localhost:11434"
    
    # OpenAI (optional)
    openai_api_key: Optional[str] = None
    
    # Anthropic (optional)
    anthropic_api_key: Optional[str] = None
    
    # Late API (Instagram posting - optional)
    late_api_key: Optional[str] = None
    late_instagram_account_id: Optional[str] = None
    
    # GitHub (optional)
    github_token: Optional[str] = None
    
    # Kie.ai (Video Generation - optional)
    kie_api_key: Optional[str] = None
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()
