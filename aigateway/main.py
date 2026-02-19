"""
AI Gateway - Main Application
ESB for AI/LLM orchestration with MCP integration
"""

import asyncio
import json
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
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
from .api.alerts import router as alerts_router
from .providers.manager import ProviderManager
from .providers.health import tracker as health_tracker
from .monitoring.health_monitor import health_monitor_loop
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

# Initialize FastAPI app — disable built-in docs so we can serve custom ones with back nav
app = FastAPI(
    title="OpenClaw Hub",
    description="Unified middleware for multi-LLM orchestration with MCP integration",
    version="0.1.0",
    docs_url=None,    # replaced by custom /docs route below
    redoc_url=None,   # replaced by custom /redoc route below
)

# Global instances (initialized on startup)
provider_manager: ProviderManager = None
workflow_engine: WorkflowEngine = None
workflow_loader: WorkflowLoader = None
mcp_manager: MCPManager = None
_health_probe_task: asyncio.Task = None
_health_monitor_task: asyncio.Task = None

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
app.include_router(alerts_router)


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


_BACK_NAV_BAR = """
<div style="
    position:sticky;top:0;z-index:999;
    background:#0a0e17;
    border-bottom:1px solid #1e2d3d;
    padding:10px 24px;
    display:flex;align-items:center;gap:12px;
    font-family:'DM Sans',system-ui,sans-serif;
">
    <a href="/" style="
        display:inline-flex;align-items:center;gap:8px;
        color:#22d3ee;font-size:13px;font-weight:600;
        text-decoration:none;
        padding:6px 12px;border:1px solid rgba(34,211,238,0.3);border-radius:6px;
    ">← OpenClaw Hub</a>
    <span style="color:#334155;font-size:13px">/ {page_name}</span>
</div>
"""

_LANDING_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OpenClaw Hub</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background: #0a0e17;
            color: #e2e8f0;
            font-family: 'DM Sans', system-ui, sans-serif;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 24px;
        }
        .container { max-width: 760px; width: 100%; }
        .brand {
            text-align: center;
            margin-bottom: 48px;
        }
        .brand-logo {
            font-size: 13px;
            font-weight: 700;
            color: #22d3ee;
            letter-spacing: .1em;
            text-transform: uppercase;
            margin-bottom: 12px;
        }
        .brand-title {
            font-size: 42px;
            font-weight: 700;
            letter-spacing: -.03em;
            line-height: 1.1;
            margin-bottom: 10px;
        }
        .brand-title span { color: #22d3ee; }
        .brand-sub {
            font-size: 16px;
            color: #64748b;
            max-width: 480px;
            margin: 0 auto;
            line-height: 1.6;
        }
        .version {
            display: inline-block;
            margin-top: 14px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            color: #22d3ee;
            background: rgba(34,211,238,0.08);
            border: 1px solid rgba(34,211,238,0.2);
            border-radius: 4px;
            padding: 4px 10px;
        }
        .cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 14px;
            margin-bottom: 40px;
        }
        .card {
            background: #111827;
            border: 1px solid #1e2d3d;
            border-radius: 14px;
            padding: 24px 20px;
            text-decoration: none;
            color: inherit;
            cursor: pointer;
            transition: border-color .2s, transform .2s, box-shadow .2s;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .card:hover {
            border-color: #22d3ee;
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(34,211,238,0.08);
        }
        .card-icon { font-size: 24px; }
        .card-title { font-size: 15px; font-weight: 700; }
        .card-desc { font-size: 12px; color: #64748b; line-height: 1.5; }
        .card-url {
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            color: #22d3ee;
            margin-top: auto;
            padding-top: 8px;
        }
        .health-card .card-title { display: flex; align-items: center; gap: 8px; }
        .health-dot {
            width: 9px; height: 9px;
            border-radius: 50%;
            background: #64748b;
            display: inline-block;
            flex-shrink: 0;
        }
        .health-dot.ok { background: #34d399; box-shadow: 0 0 8px rgba(52,211,153,0.5); }
        .health-dot.err { background: #f87171; box-shadow: 0 0 8px rgba(248,113,113,0.5); }
        .footer {
            text-align: center;
            font-size: 12px;
            color: #334155;
        }
        .footer a { color: #22d3ee; text-decoration: none; }
        @media (max-width: 480px) {
            .brand-title { font-size: 30px; }
            .cards { grid-template-columns: 1fr 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="brand">
            <div class="brand-logo">🌿 OpenClaw</div>
            <h1 class="brand-title">OpenClaw <span>Hub</span></h1>
            <p class="brand-sub">Unified API gateway for multi-LLM orchestration, social automation, image &amp; video generation, and more.</p>
            <span class="version">v0.1.0</span>
        </div>

        <div class="cards">
            <a class="card" href="/dashboard">
                <div class="card-icon">📊</div>
                <div class="card-title">Dashboard</div>
                <div class="card-desc">Monitor connections, usage, costs, and activity.</div>
                <div class="card-url">/dashboard</div>
            </a>
            <a class="card" href="/docs">
                <div class="card-icon">⚡</div>
                <div class="card-title">API Explorer</div>
                <div class="card-desc">Interactive Swagger UI — try any endpoint live.</div>
                <div class="card-url">/docs</div>
            </a>
            <a class="card" href="/redoc">
                <div class="card-icon">📖</div>
                <div class="card-title">API Reference</div>
                <div class="card-desc">Full API reference with request/response schemas.</div>
                <div class="card-url">/redoc</div>
            </a>
            <div class="card health-card" onclick="window.open('/health','_blank')">
                <div class="card-icon">🔍</div>
                <div class="card-title">
                    <span class="health-dot" id="health-dot"></span>
                    Health
                </div>
                <div class="card-desc" id="health-desc">Checking status…</div>
                <div class="card-url">/health</div>
            </div>
        </div>

        <div class="footer">
            OpenClaw Hub runs locally on your machine. &nbsp;|&nbsp;
            <a href="https://docs.openclaw.ai" target="_blank">Docs</a> &nbsp;·&nbsp;
            <a href="https://github.com/openclaw-community/openclaw-hub" target="_blank">GitHub</a>
        </div>
    </div>

    <script>
        async function checkHealth() {
            const dot = document.getElementById('health-dot');
            const desc = document.getElementById('health-desc');
            try {
                const r = await fetch('/health');
                const d = await r.json();
                if (r.ok && d.status === 'healthy') {
                    dot.className = 'health-dot ok';
                    desc.textContent = 'Hub is running and healthy.';
                } else {
                    dot.className = 'health-dot err';
                    desc.textContent = 'Hub returned an error.';
                }
            } catch {
                dot.className = 'health-dot err';
                desc.textContent = 'Hub is unreachable.';
            }
        }
        checkHealth();
        setInterval(checkHealth, 30000);
    </script>
</body>
</html>"""


@app.get("/", include_in_schema=False)
async def root(request: Request):
    """
    Content-negotiated root endpoint.
    - Browsers (Accept: text/html) → visual landing page
    - API clients (Accept: application/json or no preference) → JSON metadata
    """
    accept = request.headers.get("accept", "")
    if "text/html" in accept and "application/json" not in accept.split(",")[0]:
        return HTMLResponse(_LANDING_PAGE)
    return JSONResponse({
        "name": "OpenClaw Hub",
        "version": "0.1.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
        "dashboard": "/dashboard",
    })


@app.get("/docs", include_in_schema=False)
async def custom_swagger():
    """Swagger UI with back-navigation to landing page."""
    html = get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="OpenClaw Hub — API Explorer",
    )
    # Inject the back-nav bar into the Swagger HTML
    back_bar = _BACK_NAV_BAR.format(page_name="API Explorer")
    injected = html.body.decode().replace("<body>", f"<body>{back_bar}", 1)
    return HTMLResponse(injected)


@app.get("/redoc", include_in_schema=False)
async def custom_redoc():
    """ReDoc API reference with back-navigation to landing page."""
    html = get_redoc_html(
        openapi_url="/openapi.json",
        title="OpenClaw Hub — API Reference",
    )
    back_bar = _BACK_NAV_BAR.format(page_name="API Reference")
    injected = html.body.decode().replace("<body>", f"<body>{back_bar}", 1)
    return HTMLResponse(injected)


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
    global provider_manager, workflow_engine, workflow_loader, mcp_manager, _health_probe_task, _health_monitor_task

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

    # Start background health probe task (Issue #26 — self-healing)
    _health_probe_task = asyncio.create_task(_health_probe_loop())
    logger.info("health_probe_task_started",
                interval_seconds=settings.health_probe_interval_seconds)

    # Start background health monitor task (Issue #29 — push notifications)
    _health_monitor_task = asyncio.create_task(health_monitor_loop())
    logger.info("health_monitor_task_started",
                interval_seconds=settings.alert_check_interval_seconds,
                enabled=settings.alert_enabled)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global provider_manager, mcp_manager, _health_probe_task, _health_monitor_task

    logger.info("ai_gateway_shutting_down")

    # Cancel background tasks
    for task in (_health_probe_task, _health_monitor_task):
        if task and not task.done():
            task.cancel()
            try:
                await task
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
