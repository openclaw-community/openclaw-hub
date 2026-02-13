# AI Gateway Documentation

Welcome to the AI Gateway documentation!

## 📖 Documentation Access

### For AI Agents
**Start here:** `GET http://127.0.0.1:8080/v1/usage`

This single endpoint returns complete usage instructions, all capabilities, discovery patterns, examples, and best practices specifically designed for AI agents.

### For Humans
- **[Interactive API Explorer](http://127.0.0.1:8080/docs)** - Swagger UI (when server running)
- **[Clean Documentation](http://127.0.0.1:8080/redoc)** - ReDoc format
- **[OpenAPI Specification](http://127.0.0.1:8080/openapi.json)** - Machine-readable spec

### Discovery Endpoints
Each capability domain has its own discovery endpoint:
- `GET /v1/models` - List available LLM models
- `GET /v1/workflows` - List orchestration workflows
- `GET /v1/github/capabilities` - GitHub integration capabilities
- `GET /v1/social/capabilities` - Instagram/social media capabilities
- `GET /v1/videos/capabilities` - Video generation status

## Quick Links

- **[Getting Started](../README.md)** - Installation and quick start
- **[Contributing](../CONTRIBUTING.md)** - How to contribute
- **[Security Policy](../SECURITY.md)** - Security guidelines
- **[Changelog](../CHANGELOG.md)** - Version history

## Core Documentation

### User Guides

- **[README.md](../README.md)** - Project overview and quick start
- **[MCP Integration Guide](../MCP-INTEGRATION.md)** - Using external tools with MCP
- **[Workflow Guide](../pipelines/README.md)** - Creating YAML workflows

### Developer Guides

- **[MVP Plan](../MVP-PLAN.md)** - Original 4-week development plan
- **[Status](../STATUS.md)** - Current project status and roadmap
- **[Contributing](../CONTRIBUTING.md)** - Development setup and guidelines
- **[Test Results](../TEST-RESULTS.md)** - Testing documentation

### Reference

- **[API Documentation](http://localhost:8080/docs)** - Interactive API docs (when server running)
- **[OpenAPI Spec](http://localhost:8080/openapi.json)** - Machine-readable API spec

## Architecture

### System Overview

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ HTTP/REST
       ↓
┌─────────────────────────────────────┐
│        AI Gateway (FastAPI)         │
│  ┌──────────────────────────────┐  │
│  │     API Layer                │  │
│  │  /v1/chat/completions        │  │
│  │  /v1/pipelines/*             │  │
│  │  /v1/mcp/*                   │  │
│  └──────────────┬───────────────┘  │
│                 │                   │
│  ┌──────────────┴───────────────┐  │
│  │   Provider Manager           │  │
│  │   (Automatic Routing)        │  │
│  └──┬────────┬────────┬────────┘  │
│     │        │        │            │
│  ┌──▼──┐  ┌─▼───┐  ┌─▼────┐      │
│  │Ollam│  │OpenA│  │Anthro│      │
│  │a    │  │I    │  │pic   │      │
│  └──┬──┘  └──┬──┘  └──┬───┘      │
│     │        │        │            │
│  ┌──▼────────▼────────▼─────────┐ │
│  │   Workflow Orchestration     │ │
│  │   (Sequential Execution)     │ │
│  └──────────┬───────────────────┘ │
│             │                      │
│  ┌──────────▼───────────────────┐ │
│  │   MCP Manager                │ │
│  │   (External Tools)           │ │
│  └──────────┬───────────────────┘ │
│             │                      │
│  ┌──────────▼───────────────────┐ │
│  │   Database (SQLite)          │ │
│  │   (Metrics & Logs)           │ │
│  └──────────────────────────────┘ │
└─────────────────────────────────────┘
       │           │           │
       ↓           ↓           ↓
  ┌────────┐  ┌────────┐  ┌────────┐
  │ Ollama │  │ OpenAI │  │Anthropic│
  │ Local  │  │  API   │  │   API  │
  └────────┘  └────────┘  └────────┘
```

### Component Descriptions

**API Layer** (`aigateway/api/`)
- REST endpoints for clients
- Request validation and response formatting
- OpenAPI documentation generation

**Provider Manager** (`aigateway/providers/`)
- Automatic routing based on model names
- Provider abstraction layer
- Cost tracking and token counting

**Workflow Engine** (`aigateway/orchestration/`)
- YAML workflow parsing and execution
- Variable substitution
- Sequential step execution with context passing

**MCP Manager** (`aigateway/mcp/`)
- Model Context Protocol integration
- External tool management and execution
- Server connection lifecycle

**Storage** (`aigateway/storage/`)
- SQLite database for metrics
- Request/response logging
- Cost analytics

## Key Concepts

### Provider Routing

AI Gateway automatically routes requests to the appropriate provider based on model name:

```python
# Routes to Ollama (local, free)
{"model": "qwen2.5:32b-instruct"}

# Routes to OpenAI
{"model": "gpt-4o-mini"}

# Routes to Anthropic
{"model": "claude-sonnet"}
```

### Cost Optimization

Smart routing enables significant cost savings:

```
Before (all GPT-4):
  100 requests × $0.03 = $3.00

After (smart routing):
  80 requests × $0.00 (Ollama) = $0.00
  20 requests × $0.0001 (Claude Haiku) = $0.002
  Total: $0.002 (99% savings!)
```

### Workflow Orchestration

YAML workflows enable complex multi-step operations:

```yaml
steps:
  - id: fetch
    type: mcp_tool
    tool: fetch_url
    params:
      url: ${input.url}
    output: content

  - id: analyze
    type: llm
    model: qwen2.5:32b-instruct
    prompt: "Analyze: ${content}"
    output: result
```

### MCP Integration

Model Context Protocol enables AI to use external tools:

- **Web Search**: Brave Search, Google
- **File Access**: Read/write local files
- **APIs**: GitHub, databases, custom services
- **System Tools**: Execute commands, check status

## Configuration

### Environment Variables

Required in `.env`:

```bash
# Server
HOST=127.0.0.1
PORT=8080
RELOAD=true

# Database
DATABASE_URL=sqlite+aiosqlite:///./aigateway.db

# Providers
OLLAMA_URL=http://localhost:11434
OPENAI_API_KEY=sk-...              # Optional
ANTHROPIC_API_KEY=sk-ant-...       # Optional

# Logging
LOG_LEVEL=INFO
```

### Provider Configuration

Each provider can be configured independently:

**Ollama**: Local LLM provider
- No API key required
- Runs on your hardware
- Free to use
- Configure URL in .env

**OpenAI**: Cloud LLM provider
- Requires API key
- Pay per token
- High performance
- Multiple model options

**Anthropic**: Cloud LLM provider
- Requires API key
- Pay per token
- Claude models
- Strong reasoning capabilities

## API Reference

### Core Endpoints

**Usage Instructions (AI Agents)**
```bash
GET /v1/usage
→ Complete usage guide with all capabilities, examples, and discovery endpoints
```

**Health Check**
```bash
GET /health
→ {"status": "healthy", "timestamp": "..."}
```

**List Models**
```bash
GET /v1/models
→ {"models": {"ollama": [...], "openai": [...], "anthropic": [...]}}
```

**Chat Completion**
```bash
POST /v1/chat/completions
{
  "model": "qwen2.5:32b-instruct",
  "messages": [{"role": "user", "content": "Hello"}],
  "max_tokens": 100
}
```

**Execute Workflow**
```bash
POST /v1/workflow/summarize
{
  "input": {"text": "Long text to summarize..."}
}
```

## Deployment

### Development

```bash
# Clone repository
git clone https://github.com/openclaw-community/openclaw-hub.git
cd openclaw-hub

# Setup
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your settings

# Run
uvicorn aigateway.main:app --reload
```

### Production

See [DEPLOYMENT.md](DEPLOYMENT.md) (coming soon) for:
- Docker deployment
- Kubernetes setup
- Reverse proxy configuration
- Monitoring and logging
- Backup strategies

## Performance

### Benchmarks

Typical response times:

| Provider | Model | Tokens | Latency | Cost |
|----------|-------|--------|---------|------|
| Ollama | Qwen 2.5 32B | 100 | ~10s | $0.00 |
| OpenAI | GPT-4o-mini | 100 | ~1s | $0.0001 |
| Anthropic | Claude Haiku | 100 | ~0.7s | $0.0004 |

### Optimization Tips

1. **Use local models** for batch processing
2. **Cache responses** for repeated queries
3. **Smart routing** to cheapest capable model
4. **Workflow batching** to reduce API calls
5. **Connection pooling** for high throughput

## Troubleshooting

### Common Issues

**Server won't start**
- Check port 8080 is available
- Verify Python 3.12+ installed
- Check .env configuration

**Provider errors**
- Verify API keys in .env
- Check provider service status
- Review logs for details

**Workflow failures**
- Validate YAML syntax
- Check variable names match
- Ensure MCP servers connected

### Debug Mode

Enable verbose logging:

```bash
# In .env
LOG_LEVEL=DEBUG

# Or environment variable
LOG_LEVEL=DEBUG uvicorn aigateway.main:app
```

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for:
- Development setup
- Coding standards
- Testing guidelines
- Pull request process

## Community

- **GitHub**: https://github.com/openclaw-community/openclaw-hub
- **Issues**: Report bugs and request features
- **Discussions**: Ask questions and share ideas
- **Pull Requests**: Contribute code and documentation

## License

Apache License 2.0 - see [LICENSE](../LICENSE)

---

**Documentation Version**: 1.0.0  
**Last Updated**: 2026-02-12
