# AI Gateway

AI-specific ESB middleware for multi-LLM orchestration with MCP integration.

## 🔗 GitHub Repository

**Repository:** https://github.com/openclaw-community/openclaw-hub

**Workflow:**
```bash
# After making changes, always commit and push:
git add .
git commit -m "Your descriptive message"
git push origin main

# To pull latest changes:
git pull origin main

# Check status:
git status
```

## Features
- ✅ **Multi-Provider Support**: OpenAI, Anthropic, Ollama (local)
- ✅ **Automatic Routing**: Intelligent model-based provider selection
- ✅ **Cost Tracking**: Real-time cost calculation and metrics
- ✅ **OpenAI-Compatible API**: Drop-in replacement for OpenAI SDK
- ✅ **Database Logging**: SQLite storage for all requests
- 🚧 YAML-based workflow orchestration (Week 3)
- 🚧 MCP tool integration (Week 4)

## Quick Start

### Installation
```bash
# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create `.env` file (copy from `.env.example`):
```bash
cp .env.example .env
```

Edit `.env` and add your API keys (optional - Ollama works without keys):
```bash
# OpenAI (optional)
OPENAI_API_KEY=sk-...

# Anthropic (optional)
ANTHROPIC_API_KEY=sk-ant-...
```

### Run Server
```bash
# Development mode (auto-reload)
uvicorn aigateway.main:app --host 127.0.0.1 --port 8080 --reload
```

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
├── orchestration/    # Workflow engine (TODO)
├── mcp/             # MCP integration (TODO)
├── config.py        # Settings management ✅
└── main.py          # Application entry point
```

## Development

**Current Status**: Week 1 - Foundation ✅
- [x] Project structure
- [x] FastAPI skeleton
- [x] SQLite database
- [x] Ollama provider
- [x] Basic completion endpoint

**Next**: Week 2 - Additional Providers
- [ ] OpenAI provider
- [ ] Anthropic provider
- [ ] Smart routing logic

## Configuration

Currently using hardcoded defaults:
- **Ollama**: http://192.168.68.72:11434
- **Database**: ./aigateway.db (SQLite)
- **Port**: 8080 (localhost only)

Configuration file support coming in Week 2.
