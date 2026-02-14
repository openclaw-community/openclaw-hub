# Changelog

All notable changes to AI Gateway will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.4.0] - 2026-02-14

### Added
- **Video Generation Integration** (Kie.ai)
  - **Google VEO 3.1** support via Kie.ai
    - `veo3_fast`: Cost-efficient model (~$0.20/5s, recommended)
    - `veo3`: Highest quality model (~$0.30/5s)
    - Native vertical video (true 9:16 support)
    - Text-to-video and image-to-video generation
    - Multilingual prompt support
    - Background audio included by default
    - 1080p default, 4K available
    - 25% of Google's direct API pricing
  - **Kling 2.6** support via Kie.ai
    - Alternative video generation model ($0.28/5s)
    - 5, 10, or 20 second durations
    - Aspect ratios: 16:9, 9:16, 1:1
    - Optional audio generation
  - New `KieProvider` class for video generation
  - Async task polling with status tracking
  - Automatic cost calculation
  - Production-ready video endpoint (`/v1/videos/generations`)
  - Updated capabilities endpoint with model recommendations

### Changed
- Video generation status changed from "framework_ready" to "production_ready"
- VEO 3.1 Fast set as default/recommended model
- Updated video endpoint documentation with usage examples

## [1.3.1] - 2026-02-14

### Fixed
- **Ollama Provider**: Fixed OpenAI-compatible API integration
  - Changed endpoint from `/api/chat` to `/v1/chat/completions`
  - Switched to OpenAI-compatible request/response format
  - Added `"local"` → `"qwen2.5:32b-instruct"` model name translation
  - Resolves timeout issues with cron jobs using local model
  - Tested with Ollama v0.16.1+

## [1.3.0] - 2026-02-13

### Added
- **Auto-Start Installation Scripts**
  - `install-macos.sh`: LaunchAgent installer for macOS
  - `install-linux.sh`: systemd service installer for Linux
  - Comprehensive `docs/INSTALLATION.md` guide
  - Windows instructions (Task Scheduler, NSSM)
  - One-command installation with automatic startup on boot
- System service management commands for all platforms
- Health check verification in installers
- Troubleshooting section in installation docs

### Changed
- Updated README.md Quick Start section with auto-start option
- Installation now recommended over manual startup for production

### Fixed
- **Hub not restarting after system reboots** - Major stability improvement
- Services now survive system updates and restarts
- Prevents backup/cron job failures due to Hub unavailability

## [1.2.0] - 2026-02-12

### Added
- **AI Agent Discovery Endpoint**: `GET /v1/usage`
  - Complete usage instructions for AI agents
  - All capabilities documented in single endpoint
  - Discovery patterns and best practices
  - Request/response examples
  - Makes Hub fully self-discoverable for autonomous agents
- New documentation: `docs/AI-AGENT-DISCOVERY.md`
- Updated README.md with prominent documentation section
- Updated all documentation with discovery pattern guidance

### Changed
- Reorganized documentation to separate human vs AI agent docs
- TOOLS.md updated with discovery endpoint instructions
- Total endpoints: 28 (was 27)

## [1.1.0] - 2026-02-12

### Added
- **Image Generation** (`aigateway/images/`)
  - DALL-E 2 and DALL-E 3 support
  - HD quality up to 1792x1024
  - OpenAI-compatible API format
  - Endpoint: `POST /v1/images/generations`
  - Dogfooded: Used to generate Hub's own Instagram post

- **Instagram Integration** (`aigateway/social/`)
  - Post images, carousels, videos via Late.dev
  - Media upload support with presigned URLs
  - Scheduled posting capability
  - Endpoints:
    - `POST /v1/social/instagram/post`
    - `POST /v1/social/instagram/upload`
    - `GET /v1/social/capabilities`

- **GitHub Integration** (`aigateway/github/`)
  - Full REST API v3 wrapper
  - Repository management (list, get details)
  - Issue management (list, get, create, update)
  - Pull request management (list, get)
  - Code and issue search across GitHub
  - 12 new endpoints total
  - Capability discovery: `GET /v1/github/capabilities`
  - Rate limits: 5000 req/hr (standard), 30 req/min (search)

- **Video Generation Framework** (`aigateway/videos/`)
  - API structure ready for Sora integration
  - Alternative provider (Kie.ai) documented
  - Capability discovery: `GET /v1/videos/capabilities`
  - Awaiting OpenAI Sora API access

- New documentation files:
  - `GITHUB-INTEGRATION.md` - GitHub usage guide
  - Integration examples in README

### Changed
- Repository naming: Standardized on "openclaw-hub" everywhere
- Local folder renamed: `ai-middleware/` → `openclaw-hub-live/`
- Updated MEMORY.md with Hub discovery pattern
- Project officially named "OpenClaw Hub" (was "AI Gateway")

### Public Launch
- Published to GitHub under Apache 2.0 license
- LinkedIn article by Matthew Grunert
- Instagram launch post (generated via Hub itself)
- Repository: https://github.com/openclaw-community/openclaw-hub

### Security
- GitHub token configuration added (GITHUB_TOKEN)
- Late API key configuration added (LATE_API_KEY)
- All credentials managed via .env file
- Never exposed in logs or error messages

## [1.0.0] - 2026-02-11

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
| 1.2.0   | 2026-02-12 | AI agent discovery endpoint, self-documentation |
| 1.1.0   | 2026-02-12 | Image gen, Instagram, GitHub, public launch |
| 1.0.0   | 2026-02-11 | Production release, LLM routing, workflows, MCP |
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

[Unreleased]: https://github.com/openclaw-community/openclaw-hub/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/openclaw-community/openclaw-hub/releases/tag/v1.2.0
[1.1.0]: https://github.com/openclaw-community/openclaw-hub/releases/tag/v1.1.0
[1.0.0]: https://github.com/openclaw-community/openclaw-hub/releases/tag/v1.0.0
[0.1.0]: https://github.com/openclaw-community/openclaw-hub/releases/tag/v0.1.0
