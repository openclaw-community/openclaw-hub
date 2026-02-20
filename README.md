# OpenClaw Hub

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org)
[![Release](https://img.shields.io/github/v/release/openclaw-community/openclaw-hub)](https://github.com/openclaw-community/openclaw-hub/releases)

> AI-specific ESB middleware for multi-LLM orchestration with MCP integration

**Save 90% on AI costs** by intelligently routing requests to the best provider for each task.

## 🔗 Links

- **Repository**: https://github.com/openclaw-community/openclaw-hub
- **Latest Release**: https://github.com/openclaw-community/openclaw-hub/releases
- **Documentation**: See [docs/](docs) folder
- **Contributing**: See [CONTRIBUTING.md](CONTRIBUTING.md)
- **Security**: See [SECURITY.md](SECURITY.md)

---

## ⚡ One-Line Install

```bash
curl -fsSL https://raw.githubusercontent.com/openclaw-community/openclaw-hub/main/scripts/install.sh | bash
```

Works on **macOS** (Apple Silicon & Intel) and **Linux** (Ubuntu 22.04/24.04+). Requires Python 3.12+ and git.

The installer handles everything: clones the repo, creates a venv, installs dependencies, sets up a managed service (launchd on macOS / systemd on Linux), and opens the dashboard in your browser. Running it again on an existing installation performs a clean update.

> **Windows**: Use WSL2. See [docs/INSTALLATION.md](docs/INSTALLATION.md).

---

## Features

- ✅ **Multi-Provider Support**: OpenAI, Anthropic, Ollama (local), OpenRouter, LM Studio, custom
- ✅ **Automatic Routing**: Intelligent model-based provider selection
- ✅ **Self-Healing**: Auto-retry with exponential backoff, provider fallback routing, background health probes
- ✅ **Push Notifications**: Real-time alerts for consecutive errors, latency spikes, and budget thresholds — dashboard banners, webhooks, and macOS/Linux desktop notifications
- ✅ **Cost Tracking**: Real-time cost calculation, per-connection budgets with enforcement
- ✅ **OpenAI-Compatible API**: Drop-in replacement for OpenAI SDK
- ✅ **Database Logging**: SQLite storage for all requests and alerts
- ✅ **YAML Workflow Orchestration**: Human-readable multi-step pipelines
- ✅ **MCP Tool Integration**: External tool support (web search, files, APIs)
- ✅ **Web Dashboard**: Built-in monitoring UI — usage charts with historical navigation, connection management, cost tracking, alert banners
- ✅ **Connection Management**: Add, edit, and monitor 12+ service types (LLMs, media APIs, git platforms, gateways)
- ✅ **Budget Enforcement**: Per-connection daily/weekly/monthly limits; requests blocked at limit, override supported
- ✅ **Encrypted Credentials**: Fernet-encrypted API keys and tokens at rest

---

## 📖 Documentation

OpenClaw Hub is fully self-documenting!

### For Humans

- **Dashboard**: http://127.0.0.1:8080/dashboard
- **Interactive API Explorer**: http://127.0.0.1:8080/docs (Swagger UI)
- **API Reference**: http://127.0.0.1:8080/redoc
- **OpenAPI Spec**: http://127.0.0.1:8080/openapi.json

### For AI Agents

- **Usage Instructions**: `GET /v1/usage` — Returns how to use the Hub
- **Capability Discovery**:
  - `GET /v1/models` — List available LLM models
  - `GET /v1/workflows` — List available workflows
  - `GET /v1/github/capabilities` — GitHub integration details
  - `GET /v1/social/capabilities` — Instagram/social media details
  - `GET /v1/videos/capabilities` — Video generation details

---

## Quick Start

### Already installed?

Check before running any install commands:

```bash
# macOS — is Hub already a launchd service?
launchctl list | grep com.openclaw.hub

# Linux — is Hub already a systemd service?
systemctl --user status openclaw-hub

# Either platform — is it simply running?
curl http://127.0.0.1:8080/health
```

If Hub is running as a service, manage it with `launchctl` (macOS) or `systemctl` (Linux) — not `pkill`. Killing the process directly causes the service manager to immediately respawn it.

### Fresh install (recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/openclaw-community/openclaw-hub/main/scripts/install.sh | bash
```

The installer:
1. Checks for Python 3.12+ and git (exits with clear instructions if missing)
2. Clones to `~/.openclaw-hub/` (overridable via `OPENCLAW_HUB_HOME=...`)
3. Creates a venv and installs dependencies
4. Bootstraps `.env` with a generated secret key
5. Detects local Ollama automatically
6. Installs and starts a managed service
7. Health-checks Hub, then opens the dashboard in your browser

### Update

Running the installer again on an existing installation switches to update mode — pulls latest code, updates deps, restarts the service, and preserves your `.env`.

### Manual / Development install

> ⚠️ Only use this if you have **not** run the unified installer. If you have, Hub is already managed by a service — use `launchctl`/`systemctl` to control it.

```bash
git clone https://github.com/openclaw-community/openclaw-hub.git
cd openclaw-hub

python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env with your API keys (optional — Ollama works without keys)

uvicorn aigateway.main:app --host 127.0.0.1 --port 8080 --reload
```

### Uninstall

```bash
~/.openclaw-hub/scripts/uninstall.sh
```

Stops the service, backs up your `.env` and database to `~/.openclaw-hub.backup/`, then removes the installation.

---

## Service Management

Hub runs as a managed background service. Always use the service manager — never kill the process directly.

| | macOS (launchd) | Linux (systemd) |
|---|---|---|
| **Stop** | `launchctl unload ~/Library/LaunchAgents/com.openclaw.hub.plist` | `systemctl --user stop openclaw-hub` |
| **Start** | `launchctl load ~/Library/LaunchAgents/com.openclaw.hub.plist` | `systemctl --user start openclaw-hub` |
| **Status** | `launchctl list \| grep com.openclaw.hub` | `systemctl --user status openclaw-hub` |
| **Logs** | `tail -f ~/.openclaw-hub/hub.log` | `journalctl --user -u openclaw-hub -f` |

---

## API Examples

**Health Check:**

```bash
curl http://127.0.0.1:8080/health
```

**Chat Completion (Ollama — free, local):**

```bash
curl -X POST http://127.0.0.1:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "qwen2.5:32b-instruct", "messages": [{"role": "user", "content": "Say hello"}]}'
```

**Chat Completion (GPT-4o-mini — requires OpenAI API key):**

```bash
curl -X POST http://127.0.0.1:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "Explain quantum computing"}]}'
```

**Chat Completion (Claude — requires Anthropic API key):**

```bash
curl -X POST http://127.0.0.1:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "claude-sonnet", "messages": [{"role": "user", "content": "Write a haiku about AI"}]}'
```

**List active alerts:**

```bash
curl http://127.0.0.1:8080/api/alerts/active
```

**Dismiss an alert:**

```bash
curl -X POST http://127.0.0.1:8080/api/alerts/<alert_id>/dismiss
```

---

## Dashboard

Access at **http://127.0.0.1:8080/dashboard**

| Section | What's here |
|---|---|
| **Overview** | Real-time stats, token usage charts (daily/weekly/monthly with historical navigation), request distribution, connection health, active alert banners |
| **Connections** | Manage 12+ service types; import from `.env`; per-connection budget limits with progress bars |
| **Activity** | Every LLM and API call logged with model, provider, tokens, cost, latency, status |
| **Costs** | Per-model cost config, budget enforcement, spend history |

Alert banners appear on every page and dismiss without a page reload. They auto-clear when the underlying condition resolves.

---

## Self-Healing & Alerts

Hub automatically recovers from transient provider failures:

- **Retry with backoff**: failed requests retried up to 3× (1s → 5s → 15s, configurable)
- **Fallback routing**: if primary provider exhausts retries, request is routed to a fallback (e.g. `openai → ollama`)
- **Health probes**: degraded providers are probed every 30s; marked healthy after 3 consecutive successes
- **Push notifications**: background monitor checks every 60s for consecutive errors, latency spikes, and budget thresholds; alerts dispatched to dashboard, webhook, and desktop

Configure in `.env`:

```bash
# Retry
RETRY_ENABLED=true
RETRY_MAX_ATTEMPTS=3
FALLBACK_RULES=openai:ollama,anthropic:ollama

# Alerts
ALERT_ENABLED=true
ALERT_WEBHOOK_URL=https://your-endpoint.example.com/alerts
ALERT_DESKTOP_NOTIFY=true
ALERT_CONSECUTIVE_ERROR_THRESHOLD=3
ALERT_BUDGET_THRESHOLD_PERCENT=90
```

---

## Architecture

```
openclaw-hub/
├── scripts/
│   ├── install.sh                # One-line installer (macOS + Linux)
│   ├── install-macos.sh          # macOS redirect stub → install.sh
│   ├── install-linux.sh          # Linux redirect stub → install.sh
│   └── uninstall.sh              # Uninstaller with data backup
├── examples/
│   ├── summarize.yaml            # Example: text summarisation workflow
│   ├── smart-analysis.yaml       # Example: adaptive complexity routing
│   └── web-research.yaml         # Example: web fetch + LLM analysis
├── aigateway/
│   ├── api/                      # FastAPI routers
│   │   ├── completions.py        # /v1/chat/completions (retry + fallback)
│   │   ├── alerts.py             # /api/alerts/* (Issue #29)
│   │   └── dashboard.py          # /api/dashboard/* (18 endpoints)
│   ├── monitoring/               # Push notification subsystem (Issue #29)
│   │   ├── alert_manager.py      # Deduplication, auto-resolve, dispatch
│   │   ├── health_monitor.py     # Background check loop
│   │   └── channels/             # webhook.py, desktop.py
│   ├── providers/                # LLM provider implementations
│   │   ├── manager.py            # Routing + fallback
│   │   ├── health.py             # Provider health tracker (Issue #26)
│   │   ├── ollama.py
│   │   ├── openai.py
│   │   └── anthropic.py
│   ├── dashboard/
│   │   ├── data.py               # Async data access layer
│   │   └── crypto.py             # Fernet encrypt/decrypt/mask
│   ├── storage/
│   │   ├── database.py           # SQLAlchemy async setup + migrations
│   │   └── models.py             # Request, Connection, Alert, CostConfig models
│   ├── orchestration/            # YAML workflow engine
│   ├── mcp/                      # MCP integration
│   ├── static/index.html         # Dashboard UI (single-file, no build tools)
│   ├── config.py                 # Settings (pydantic-settings, .env)
│   └── main.py                   # App entry point, startup/shutdown lifecycle
└── .env.example                  # Configuration reference
```

---

## Provider Routing

Requests are routed automatically by model name:

| Model pattern | Provider |
|---|---|
| `gpt-4*`, `gpt-3.5*`, `gpt-4o*` | OpenAI |
| `claude*` | Anthropic |
| Anything else | Ollama (local) |

Fallback rules are configurable via `FALLBACK_RULES` in `.env`.

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, coding standards, and the PR process.

## License

Apache License 2.0 — see [LICENSE](LICENSE) for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/openclaw-community/openclaw-hub/issues)
- **Documentation**: See [docs/](docs) folder
- **Security**: Report vulnerabilities via [SECURITY.md](SECURITY.md)

## Project Status

**Version**: 1.2.0  
**Status**: Production-ready  
**Maintainer**: OpenClaw Community

See [CHANGELOG.md](CHANGELOG.md) for version history.
