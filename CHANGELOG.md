# Changelog

All notable changes to AI Gateway will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Open source community documentation (CONTRIBUTING.md, CODE_OF_CONDUCT.md)
- Issue and PR templates for better contribution workflow
- Comprehensive security policy (SECURITY.md)

## [1.0.0] - 2026-02-12

### Added
- Multi-provider LLM support (OpenAI, Anthropic, Ollama)
- Automatic provider routing based on model names
- Real-time cost tracking and metrics
- OpenAI-compatible API (`/v1/chat/completions`)
- SQLite database for request logging and metrics
- YAML workflow orchestration engine
- MCP (Model Context Protocol) integration for external tools
- Environment-based configuration (.env support)
- Structured JSON logging
- FastAPI server with auto-reload support
- Async architecture throughout
- Comprehensive documentation:
  - README.md - Quick start guide
  - MVP-PLAN.md - Original 4-week development plan
  - STATUS.md - Current project status
  - MCP-INTEGRATION.md - Tool integration guide
  - TEST-RESULTS.md - Testing documentation
  - SECURITY-AUDIT.md - Internal security review

### Providers
- **Ollama**: Local model support (Qwen, Llama, etc.)
- **OpenAI**: GPT-4, GPT-3.5, GPT-4o models
- **Anthropic**: Claude 3 Sonnet, Haiku, Opus

### Workflows
- Multi-step LLM orchestration
- Variable substitution (`${input.field}`)
- Sequential execution with context passing
- MCP tool integration in workflows
- Example workflows:
  - `summarize.yaml` - Two-step text summarization
  - `smart-analysis.yaml` - Adaptive complexity routing
  - `web-research.yaml` - Web fetch + LLM analysis

### API Endpoints
- `GET /health` - Health check
- `GET /` - API information
- `GET /v1/models` - List available models by provider
- `POST /v1/chat/completions` - LLM completion (OpenAI-compatible)
- `GET /v1/workflows` - List available workflows
- `POST /v1/workflow/{name}` - Execute workflow
- `POST /v1/mcp/servers` - Connect MCP server
- `GET /v1/mcp/servers` - List connected MCP servers
- `GET /v1/mcp/servers/{name}/tools` - List server tools

### Security
- Environment variable secrets management
- `.env` file excluded from version control
- Input validation on all requests
- Sensitive data redaction in logs
- Localhost-only default binding
- Security audit completed and documented

### Performance
- Async request handling
- Connection pooling for providers
- Efficient token counting
- Sub-second response times for most requests

### Fixed
- Anthropic provider: System parameter handling (null value issue)
- Git repository: Removed unnecessary files (venv/, __pycache__/)
- Security: Removed hardcoded internal IP addresses

### Changed
- Default Ollama URL: `http://localhost:11434` (was hardcoded IP)
- Repository cleaned from 6,797 to 37 files
- Documentation updated to reflect completion of all 4 development weeks

## [0.1.0] - 2026-02-08

### Added
- Initial project structure
- Basic FastAPI application
- Ollama provider implementation
- Database schema and models
- Configuration management
- Development environment setup

---

## Version History Summary

| Version | Date       | Highlights |
|---------|------------|------------|
| 1.0.0   | 2026-02-12 | Production release, all features complete |
| 0.1.0   | 2026-02-08 | Initial development version |

## Future Plans

See [STATUS.md](STATUS.md) for detailed future plans and roadmap.

### Planned for 2.0

- Streaming responses support
- Authentication and API keys
- Response caching layer
- Redis integration for distributed deployments
- Advanced workflow features (conditionals, loops)
- Additional provider support (Google Gemini, Cohere)
- Prometheus metrics export
- Docker deployment guide
- Helm charts for Kubernetes

---

## Release Notes Format

Each release should include:

**Added** - New features  
**Changed** - Changes to existing functionality  
**Deprecated** - Soon-to-be removed features  
**Removed** - Removed features  
**Fixed** - Bug fixes  
**Security** - Security improvements

---

[Unreleased]: https://github.com/openclaw-community/openclaw-hub/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/openclaw-community/openclaw-hub/releases/tag/v1.0.0
[0.1.0]: https://github.com/openclaw-community/openclaw-hub/releases/tag/v0.1.0
