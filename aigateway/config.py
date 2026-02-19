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
    
    # Late API / getlate.dev (Instagram posting - optional)
    # The Connections UI writes GETLATE_API_KEY; the legacy env var is LATE_API_KEY.
    # Both are accepted; GETLATE_API_KEY takes precedence if present.
    late_api_key: Optional[str] = None
    getlate_api_key: Optional[str] = None
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

    # Self-healing: retry with backoff (Issue #26)
    retry_enabled: bool = True
    retry_max_attempts: int = 3
    retry_backoff_base: float = 1.0       # seconds before first retry
    retry_backoff_multiplier: float = 5.0 # multiplier per attempt: 1s → 5s → 15s (approx)
    # Comma-separated HTTP status codes that trigger a retry
    retry_on_status_codes: str = "429,500,502,503,504"

    # Self-healing: fallback routing (Issue #26)
    # Format: "primary:fallback,primary2:fallback2" e.g. "openai:anthropic,anthropic:openai"
    fallback_rules: str = "openai:ollama,anthropic:ollama"

    # Self-healing: health probes (Issue #26)
    health_probe_enabled: bool = True
    health_probe_interval_seconds: int = 30    # probe interval for degraded/error connections
    health_probe_success_threshold: int = 3    # consecutive successes before marking healthy

    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = str(_ENV_FILE)
        env_file_encoding = "utf-8"
        extra = "ignore"   # Ignore unknown env vars — prevents crashes when the
                           # Connections UI writes keys not yet declared in Settings


# Global settings instance
settings = Settings()
