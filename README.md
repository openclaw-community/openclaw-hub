# OpenClaw-HUB

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org)
[![Release](https://img.shields.io/github/v/release/openclaw-community/openclaw-hub)](https://github.com/openclaw-community/openclaw-hub/releases)

> AI-specific ESB middleware for multi-LLM orchestration with MCP integration

**Save 97% on AI costs** by intelligently routing requests to the best provider for each task.

## 🔗 Links

- **Repository**: https://github.com/openclaw-community/openclaw-hub
- **Latest Release**: https://github.com/openclaw-community/openclaw-hub/releases
- **Documentation**: See [docs/](docs/) folder
- **Contributing**: See [CONTRIBUTING.md](CONTRIBUTING.md)
- **Security**: See [SECURITY.md](SECURITY.md)

## Features
- ✅ **Multi-Provider Support**: OpenAI, Anthropic, Ollama (local)
- ✅ **Automatic Routing**: Intelligent model-based provider selection
- ✅ **Cost Tracking**: Real-time cost calculation and metrics
- ✅ **OpenAI-Compatible API**: Drop-in replacement for OpenAI SDK
- ✅ **Database Logging**: SQLite storage for all requests
- ✅ **YAML Workflow Orchestration**: Human-readable multi-step pipelines
- ✅ **MCP Tool Integration**: External tool support (web search, files, APIs)

## 📖 Documentation

**OpenClaw Hub is fully self-documenting!**

### For Humans
- **Interactive API Explorer**: http://127.0.0.1:8080/docs (Swagger UI)
- **Clean Documentation**: http://127.0.0.1:8080/redoc
- **OpenAPI Spec**: http://127.0.0.1:8080/openapi.json

### For AI Agents
- **Usage Instructions**: `GET /v1/usage` - Returns how to use the Hub
- **Capability Discovery**:
  - `GET /v1/models` - List available LLM models
  - `GET /v1/workflows` - List available workflows
  - `GET /v1/github/capabilities` - GitHub integration details
  - `GET /v1/social/capabilities` - Instagram/social media details
  - `GET /v1/videos/capabilities` - Video generation details

**Start here:** All 27 endpoints include complete request/response schemas, examples, and validation rules.

## Quick Start

### Installation

> **Already installed?** Check first before running any install commands:
> ```bash
> # macOS — is the Hub already a launchd service?
> launchctl list | grep openclaw.hub
>
> # Linux — is the Hub already a systemd service?
> systemctl --user status openclaw-hub
>
> # Either platform — is it simply running?
> curl http://127.0.0.1:8080/health
> ```
> If the Hub is already running as a service, use `launchctl` (macOS) or `systemctl` (Linux) to manage it — **not** `pkill` or manual process commands. Killing the process directly will just cause the service manager to respawn it immediately.

**Option 1: Auto-Start (Recommended for Production)**

Install as a system service that starts automatically on boot:

```bash
# Clone repository
git clone https://github.com/openclaw-community/openclaw-hub.git
cd openclaw-hub

# Create virtual environment and install
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure API keys (optional)
cp .env.example .env
# Edit .env with your keys

# Run platform-specific installer
./install-macos.sh   # macOS
./install-linux.sh   # Linux
# See docs/INSTALLATION.md for Windows
```

**Option 2: Manual/Development**

> ⚠️ **Only use this if you have NOT run `install-macos.sh` or `install-linux.sh`.** If you have, the Hub is already managed by a service manager — use Option 1's management commands instead.

```bash
# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your API keys (optional - Ollama works without keys)

# Run server
uvicorn aigateway.main:app --host 127.0.0.1 --port 8080 --reload
```

📖 **Full installation guide**: [docs/INSTALLATION.md](docs/INSTALLATION.md)

### Test Endpoints

**Health Check:**
```bash
curl http://localhost:8080/health
```

**List Models (by provider):**
```bash
curl http://localhost:8080/v1/models
# Returns: {"models": {"ollama": [...], "openai": [...], "anthropic": [...]}}
```

**Chat Completion (Ollama - free):**
```bash
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5:32b-instruct",
    "messages": [
      {"role": "user", "content": "Say hello in 5 words"}
    ],
    "max_tokens": 100
  }'
```

**Chat Completion (GPT-4 - requires API key):**
```bash
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [
      {"role": "user", "content": "Explain quantum computing"}
    ],
    "max_tokens": 200
  }'
```

**Chat Completion (Claude - requires API key):**
```bash
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-sonnet",
    "messages": [
      {"role": "user", "content": "Write a haiku about AI"}
    ],
    "max_tokens": 100
  }'
```

## How It Works

### Automatic Provider Routing

The gateway automatically routes requests based on the model name:

| Model Pattern | Provider | Example |
|--------------|----------|---------|
| `gpt-4*`, `gpt-3.5*` | OpenAI | `gpt-4o-mini`, `gpt-4-turbo` |
| `claude*` | Anthropic | `claude-sonnet`, `claude-haiku` |
| Everything else | Ollama | `qwen2.5:32b-instruct`, `llama3.2:1b` |

**Example:**
```bash
# This goes to Ollama (free, local)
"model": "qwen2.5:32b-instruct"

# This goes to OpenAI (paid, requires API key)
"model": "gpt-4o-mini"

# This goes to Anthropic (paid, requires API key)
"model": "claude-sonnet"
```

### Cost Tracking

Every request is logged with:
- Prompt tokens
- Completion tokens
- Total cost in USD
- Latency in milliseconds
- Provider used

**View costs:**
```bash
sqlite3 aigateway.db "SELECT model, SUM(cost_usd) as total_cost, COUNT(*) as requests FROM requests GROUP BY model;"
```

## Dashboard

OpenClaw Hub includes a built-in web dashboard for monitoring and managing your connections.

**Access:** Navigate to `http://127.0.0.1:8080/dashboard` after starting the server.

**Features:**
- Real-time overview of token usage, request counts, and estimated costs
- Visual charts for usage trends (daily, weekly, monthly)
- Connection management — add, edit, disable, or remove service connections
- Support for diverse service types: LLM providers, media APIs, Git platforms, gateways, and custom services
- Import existing connections from your `.env` configuration
- Per-model cost-per-token configuration
- Budget alerts with daily, weekly, and monthly limits

## Architecture

```
aigateway/
├── api/              # FastAPI routes
│   └── completions.py    # /v1/chat/completions
├── providers/        # LLM provider implementations
│   ├── base.py           # Abstract interface
│   ├── ollama.py         # Ollama (local) ✅
│   ├── openai.py         # OpenAI ✅
│   ├── anthropic.py      # Anthropic ✅
│   └── manager.py        # Provider routing ✅
├── storage/          # Database models & migrations
│   ├── database.py       # SQLAlchemy setup
│   └── models.py         # Request/Workflow models
├── orchestration/    # Workflow engine ✅
├── mcp/             # MCP integration ✅
├── config.py        # Settings management ✅
└── main.py          # Application entry point
```

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Development setup
- Coding standards
- Pull request process
- Testing guidelines

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/openclaw-community/openclaw-hub/issues)
- **Documentation**: See [docs/](docs/) folder
- **Security**: Report vulnerabilities via [SECURITY.md](SECURITY.md)

## Project Status

**Version**: 1.0.0  
**Status**: Core features production-ready; orchestration engine and MCP integration in development  
**Maintainer**: OpenClaw Community

See [docs/STATUS.md](docs/STATUS.md) for detailed development history and [CHANGELOG.md](CHANGELOG.md) for version history.
