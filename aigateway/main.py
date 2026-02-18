"""
AI Gateway - Main Application
ESB for AI/LLM orchestration with MCP integration
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import structlog
from datetime import datetime
from .storage.database import init_database
from .api.completions import router as completions_router
from .api.workflows import router as workflows_router
from .api.mcp import router as mcp_router
from .api.images import router as images_router
from .api.social import router as social_router
from .api.videos import router as videos_router
from .api.github import router as github_router
from .api.usage import router as usage_router
from .api.config_status import router as config_status_router
from .providers.manager import ProviderManager
from .orchestration.engine import WorkflowEngine
from .orchestration.loader import WorkflowLoader
from .mcp.manager import MCPManager
from .config import settings

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
        "health": "/health"
    }


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global provider_manager, workflow_engine, workflow_loader, mcp_manager
    
    logger.info("ai_gateway_starting", version="0.1.0")
    
    # Initialize database
    await init_database()
    
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


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global provider_manager, mcp_manager
    
    logger.info("ai_gateway_shutting_down")
    
    if provider_manager:
        await provider_manager.close_all()
    
    if mcp_manager:
        await mcp_manager.close_all()


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
