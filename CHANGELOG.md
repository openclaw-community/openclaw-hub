# Changelog

All notable changes to AI Gateway will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-02-19

### Added
- **Non-LLM API traffic instrumentation** (#30): New `api_calls` table captures every GitHub, social, video, and other non-LLM request through Hub — service, operation, endpoint, method, status code, latency, cost, and metadata
- **Non-LLM traffic in dashboard** (#31): Activity feed and usage charts now include non-LLM API calls alongside LLM completions; per-service breakdown in charts
- **Per-connection budget enforcement** (#32): Daily, weekly, and monthly spend limits per connection; requests blocked at limit with structured `429` response; budget override (resume) endpoint; auto-created `$0.00` cost entries on connection add; budget progress bars and blocked/warning banners in dashboard
- **Chart historical navigation** (#33): Weekly and monthly chart views gain ← / → period navigation and a "Current" jump button; week view shows 7 daily stacked bars; month view renders a stacked area chart; daily view preserves the existing 30-day trend
- **Visual landing page** (#27): `GET /` now returns a styled HTML landing page for browsers (with health dot live-check) and JSON metadata for API clients — content-negotiated via `Accept` header; Swagger and ReDoc get back-navigation bars
- **Self-healing** (#26): Auto-retry with configurable exponential backoff (default: 3 attempts, 1s → 5s → 15s); provider fallback routing on retry exhaustion; background health probe loop for degraded providers; startup state file for unexpected-restart detection; `X-Hub-Fallback`, `X-Hub-Original-Provider`, `X-Hub-Actual-Provider` response headers when fallback was used
- **Push notifications** (#29): Background health monitor checks all enabled connections every 60s for consecutive errors, latency spikes, and budget threshold breaches; `AlertManager` with 15-minute deduplication window and auto-resolve when conditions clear; webhook POST channel; macOS `osascript` / Linux `notify-send` desktop notification channel; `Alert` database table; five new API endpoints under `/api/alerts/`; persistent alert banners on all dashboard views with 30-second live poll and dismiss button
- **One-line installer** (#28): `curl -fsSL .../install.sh | bash` handles full end-to-end setup on macOS and Linux — preflight checks (Python 3.12+, git), clone to `~/.openclaw-hub/`, venv creation, dependency install, `.env` bootstrap with generated secret key, Ollama auto-detection, launchd (macOS) or systemd `--user` (Linux) service install, 30-second health poll, and browser open; idempotent update mode on re-run; `scripts/uninstall.sh` with data backup
- **Provider health tracker** (#26): In-memory per-provider health state (`HEALTHY` / `DEGRADED` / `ERROR`) with consecutive failure/success counters; `ProviderHealthTracker` singleton; lightweight provider probe functions (Ollama: `GET /api/tags`, OpenAI: list models, Anthropic: minimal completion)
- **New config fields**: `RETRY_*`, `FALLBACK_RULES`, `HEALTH_PROBE_*`, `ALERT_*` settings — all optional with sensible defaults, no `.env` changes required to run

### Changed
- `GET /v1/chat/completions` now applies budget enforcement before routing, then retries with backoff, then falls back to configured alternate provider before returning an error
- Cost config overhaul: `CostConfig` gains a `connection_id` FK (nullable for legacy rows); `Connection` gains `daily_limit_usd`, `weekly_limit_usd`, `monthly_limit_usd`, `budget_override_until`; dashboard cost table groups entries by connection
- `install-macos.sh` and `install-linux.sh` replaced with redirect stubs that delegate to `install.sh`
- `README.md` rewritten: one-line install front-and-centre, service management reference table, self-healing and alert config snippets, updated architecture diagram

### Fixed
- SQLite `foreign_keys` PRAGMA now enabled on every connection so `ON DELETE CASCADE` on `cost_configs → connections` works correctly

## [1.1.0] - 2026-02-18

### Added
- Web dashboard accessible at `http://127.0.0.1:8080/dashboard`
- Dashboard API endpoints under `/api/dashboard/*`
- Connection management with template-driven Add flow supporting 13 service types
- Import from `.env` — one-click import of existing configured providers
- Token usage charts (daily/weekly/monthly) with per-provider breakdown
- Cost-per-token configuration with per-model granularity
- Budget limits (daily/weekly/monthly) with threshold alerts
- Recent request activity feed
- Connection health monitoring
- Encrypted credential storage for API keys and tokens (Fernet symmetric encryption)
- LLM provider connections automatically sync API keys to `.env`

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
| 1.2.0   | 2026-02-19 | One-line installer, self-healing, push notifications, per-connection budgets, chart nav |
| 1.1.0   | 2026-02-18 | Web dashboard, connection management, cost tracking, encrypted credentials |
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
[1.2.0]: https://github.com/openclaw-community/openclaw-hub/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/openclaw-community/openclaw-hub/releases/tag/v1.1.0
[1.0.0]: https://github.com/openclaw-community/openclaw-hub/releases/tag/v1.0.0
[0.1.0]: https://github.com/openclaw-community/openclaw-hub/releases/tag/v0.1.0
