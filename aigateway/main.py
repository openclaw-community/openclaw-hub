"""
AI Gateway - Main Application
ESB for AI/LLM orchestration with MCP integration
"""

import asyncio
import json
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os as _os
import structlog
from datetime import datetime, timezone
from .storage.database import init_database, backfill_provider_column
from .api.completions import router as completions_router
from .api.workflows import router as workflows_router
from .api.mcp import router as mcp_router
from .api.images import router as images_router
from .api.social import router as social_router
from .api.videos import router as videos_router
from .api.github import router as github_router
from .api.usage import router as usage_router
from .api.dashboard import router as dashboard_router
from .api.config_status import router as config_status_router
from .providers.manager import ProviderManager
from .providers.health import tracker as health_tracker
from .orchestration.engine import WorkflowEngine
from .orchestration.loader import WorkflowLoader
from .mcp.manager import MCPManager
from .config import settings
from .dashboard.crypto import get_or_create_secret_key

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()

# Initialize FastAPI app
app = FastAPI(
    title="AI Gateway",
    description="Unified middleware for multi-LLM orchestration with MCP integration",
    version="0.1.0",
)

# Global instances (initialized on startup)
provider_manager: ProviderManager = None
workflow_engine: WorkflowEngine = None
workflow_loader: WorkflowLoader = None
mcp_manager: MCPManager = None
_health_probe_task: asyncio.Task = None

# Restart detection: persist last startup time so the next session can detect gaps
_STARTUP_STATE_FILE = Path(__file__).parent.parent / ".startup_state.json"
_startup_info: dict = {}  # populated on startup; exposed via /api/dashboard/stats

# Mount routers
app.include_router(usage_router, tags=["documentation"])
app.include_router(config_status_router, tags=["config"])
app.include_router(completions_router, tags=["completions"])
app.include_router(workflows_router, tags=["workflows"])
app.include_router(mcp_router, tags=["mcp"])
app.include_router(images_router, tags=["images"])
app.include_router(videos_router, tags=["videos"])
app.include_router(social_router, tags=["social"])
app.include_router(github_router, tags=["github"])
app.include_router(dashboard_router)


@app.get("/dashboard", response_class=FileResponse)
async def serve_dashboard():
    dashboard_path = _os.path.join(_os.path.dirname(__file__), "static", "index.html")
    return FileResponse(dashboard_path)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    service_manager = settings.openclaw_service_manager

    # Provide the correct restart instructions based on how the Hub is managed
    restart_instructions = {
        "launchd": {
            "stop": "launchctl unload ~/Library/LaunchAgents/com.openclaw.hub.plist",
            "start": "launchctl load ~/Library/LaunchAgents/com.openclaw.hub.plist",
            "warning": "Do NOT use pkill — launchd will immediately respawn the process.",
        },
        "systemd": {
            "stop": "systemctl --user stop openclaw-hub",
            "start": "systemctl --user start openclaw-hub",
            "restart": "systemctl --user restart openclaw-hub",
            "warning": "Do NOT kill the process directly — use systemctl to manage the service.",
        },
        "manual": {
            "note": "Hub is not running under a service manager. Manual process management applies.",
        },
    }.get(service_manager, {})

    return JSONResponse({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.1.0",
        "service": {
            "managed_by": service_manager,
            **restart_instructions,
        },
    })


@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "name": "AI Gateway",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
        "dashboard": "http://127.0.0.1:8080/dashboard"
    }


_static_dir = _os.path.join(_os.path.dirname(__file__), "static")
_os.makedirs(_static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=_static_dir), name="static")


def _record_startup():
    """Write startup timestamp and detect unexpected restarts."""
    global _startup_info
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    prev = {}

    if _STARTUP_STATE_FILE.exists():
        try:
            prev = json.loads(_STARTUP_STATE_FILE.read_text())
        except Exception:
            pass

    last_shutdown = prev.get("last_shutdown")
    last_startup = prev.get("startup_at")
    unexpected_restart = last_startup and not last_shutdown  # started before clean shutdown

    _startup_info = {
        "startup_at": now_iso,
        "previous_startup_at": last_startup,
        "previous_shutdown_at": last_shutdown,
        "unexpected_restart": unexpected_restart,
    }

    # Write new state (clear last_shutdown to detect ungraceful exit on next start)
    _STARTUP_STATE_FILE.write_text(json.dumps({"startup_at": now_iso, "last_shutdown": None}))

    if unexpected_restart:
        logger.warning("unexpected_restart_detected", previous_startup=last_startup)
        print(f"[Hub] ⚠️  Unexpected restart detected. Previous session started at {last_startup}.")
    else:
        print(f"[Hub] ✅  Started at {now_iso}" + (f" (previous shutdown: {last_shutdown})" if last_shutdown else ""))


def _record_shutdown():
    """Record graceful shutdown timestamp."""
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    if _STARTUP_STATE_FILE.exists():
        try:
            state = json.loads(_STARTUP_STATE_FILE.read_text())
            state["last_shutdown"] = now_iso
            _STARTUP_STATE_FILE.write_text(json.dumps(state))
        except Exception:
            pass
    print(f"[Hub] Graceful shutdown at {now_iso}")


async def _health_probe_loop():
    """
    Background task: probe degraded/error providers every N seconds.
    After `success_threshold` consecutive successes, marks provider healthy.
    """
    from .config import settings as cfg
    while True:
        await asyncio.sleep(cfg.health_probe_interval_seconds)
        if not cfg.health_probe_enabled or provider_manager is None:
            continue
        degraded = health_tracker.degraded_providers()
        for pname in degraded:
            if pname in provider_manager.providers:
                probe_fn = provider_manager.get_probe_fn(pname)
                recovered = await health_tracker.probe_and_recover(pname, probe_fn)
                if recovered:
                    logger.info("provider_auto_recovered", provider=pname)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global provider_manager, workflow_engine, workflow_loader, mcp_manager, _health_probe_task

    logger.info("ai_gateway_starting", version="0.1.0")

    # Restart detection
    _record_startup()

    # Initialize database
    await init_database()

    # Ensure dashboard encryption key exists
    get_or_create_secret_key()

    # Backfill provider column for existing request rows
    await backfill_provider_column()

    # Initialize provider manager
    provider_manager = ProviderManager(
        ollama_url=settings.ollama_url,
        openai_api_key=settings.openai_api_key,
        anthropic_api_key=settings.anthropic_api_key
    )

    # Log available providers
    providers = list(provider_manager.providers.keys())
    logger.info("providers_initialized", providers=providers)

    # Initialize MCP manager
    mcp_manager = MCPManager()
    logger.info("mcp_manager_initialized")

    # Initialize workflow engine with MCP support
    workflow_engine = WorkflowEngine(provider_manager, mcp_manager)
    logger.info("workflow_engine_initialized")

    # Initialize workflow loader
    workflow_loader = WorkflowLoader(workflows_dir="./pipelines")
    workflow_loader.load_all()
    logger.info("workflows_loaded", count=len(workflow_loader.workflows))

    # Start background health probe task
    _health_probe_task = asyncio.create_task(_health_probe_loop())
    logger.info("health_probe_task_started",
                interval_seconds=settings.health_probe_interval_seconds)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global provider_manager, mcp_manager, _health_probe_task

    logger.info("ai_gateway_shutting_down")

    # Cancel health probe task
    if _health_probe_task and not _health_probe_task.done():
        _health_probe_task.cancel()
        try:
            await _health_probe_task
        except asyncio.CancelledError:
            pass

    if provider_manager:
        await provider_manager.close_all()

    if mcp_manager:
        await mcp_manager.close_all()

    # Record clean shutdown so next startup doesn't flag as unexpected
    _record_shutdown()


if __name__ == "__main__":
    import uvicorn
    # settings.reload is only respected here (direct run via `python -m aigateway.main`).
    # When launched via uvicorn CLI or a service manager (launchd/systemd), pass --reload
    # explicitly on the command line if needed. Do not enable reload in production.
    uvicorn.run(
        "aigateway.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower()
    )
