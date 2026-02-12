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

# Mount routers
app.include_router(completions_router, tags=["completions"])


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.1.0"
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
    logger.info("ai_gateway_starting", version="0.1.0")
    await init_database()
    # TODO: Load workflows, connect MCP servers


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("ai_gateway_shutting_down")
    # TODO: Close database connections, cleanup resources


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",  # localhost only for security
        port=8080,
        reload=True,  # Auto-reload during development
        log_level="info"
    )
