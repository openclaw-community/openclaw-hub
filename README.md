# AI Gateway

AI-specific ESB middleware for multi-LLM orchestration with MCP integration.

## Features (MVP)
- ✅ Unified API for multiple LLM providers (OpenAI, Anthropic, Ollama)
- ✅ Cost tracking and metrics per request
- 🚧 YAML-based workflow orchestration
- 🚧 MCP tool integration
- 🚧 Analytics dashboard

## Quick Start

### Installation
```bash
# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Run Server
```bash
# Development mode (auto-reload)
python -m aigateway.main

# Or with uvicorn directly
uvicorn aigateway.main:app --host 127.0.0.1 --port 8080 --reload
```

### Test Endpoint
```bash
# Health check
curl http://localhost:8080/health

# List models
curl http://localhost:8080/v1/models

# Chat completion
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

## Architecture

```
aigateway/
├── api/              # FastAPI routes
├── providers/        # LLM provider implementations
├── storage/          # Database models & migrations
├── orchestration/    # Workflow engine (TODO)
├── mcp/             # MCP integration (TODO)
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
