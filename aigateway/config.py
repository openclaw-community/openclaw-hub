"""
Configuration management for AI Gateway
"""

import logging
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional

# Resolve .env path relative to this file's location so it loads correctly
# regardless of the working directory when uvicorn is launched.
_ENV_FILE = Path(__file__).parent.parent / ".env"

if not _ENV_FILE.exists():
    logging.warning(f"[config] .env file not found at {_ENV_FILE} — credentials will not be loaded")


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
    
    # Dashboard (optional)
    dashboard_secret_key: Optional[str] = None

    # Service manager (set automatically by install scripts; do not edit manually)
    # Values: "launchd" | "systemd" | "manual"
    openclaw_service_manager: str = "manual"

    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = str(_ENV_FILE)
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()
