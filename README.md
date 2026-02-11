# OpenClaw Hub

**The missing orchestration layer for OpenClaw and autonomous AI agents.**

[![Tests](https://github.com/openclaw-community/openclaw-hub/actions/workflows/tests.yml/badge.svg)](https://github.com/openclaw-community/openclaw-hub/actions/workflows/tests.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

## The Problem

OpenClaw is powerful but faces challenges:
- 🧠 **Memory bloat** - Documenting every integration inflates context and token costs
- 🤔 **Capability amnesia** - Frequently forgets configured API connections exist
- 🔑 **Credential sprawl** - API keys scattered across configuration files
- 🤷 **No routing intelligence** - Doesn't know when to use Sora vs Kie.ai, or which service is optimal

## The Solution

OpenClaw Hub is a single MCP server that:
- ✅ **Centralizes integrations** - One place for all API connections
- ✅ **Enables discovery** - Ask "what can I do?" instead of remembering
- ✅ **Manages credentials securely** - All API keys isolated and audited
- ✅ **Routes intelligently** - Optimizes for cost, quality, or speed automatically
- ✅ **Reduces memory** - 70-90% reduction in OpenClaw's context bloat

## Quick Start

### Installation
```bash
# Clone the repository
git clone https://github.com/openclaw-community/openclaw-hub.git
cd openclaw-hub

# Install dependencies
pip install -r requirements.txt

# Copy example configuration
cp .env.example .env
cp config/config.example.yaml config/openclaw-hub.yaml

# Edit .env with your API keys
nano .env
```

### Configuration

Edit `config/openclaw-hub.yaml`:
```yaml
domains:
  media:
    enabled: true
    default_provider: "kie"  # Cost-optimized
    
  git:
    enabled: true
    default_platform: "github"
```

Add your API keys to `.env`:
```bash
OPENAI_API_KEY=sk-your-key-here
KIE_API_KEY=your-kie-key-here
GITHUB_TOKEN=ghp_your-token-here
```

### Connect to OpenClaw

Add to your OpenClaw configuration:
```json
{
  "mcpServers": {
    "openclaw-hub": {
      "command": "python",
      "args": ["/path/to/openclaw-hub/src/server.py"],
      "env": {
        "CONFIG_PATH": "/path/to/openclaw-hub/config/openclaw-hub.yaml"
      }
    }
  }
}
```

### Usage Example

Once configured, OpenClaw can:
```
OpenClaw: What capabilities do I have?
Hub: [Returns organized list of media, git, data capabilities]

OpenClaw: Generate a video about AI existentialism, optimize for cost
Hub: [Routes to Kie.ai, generates video, returns URL and cost: $0.24]

OpenClaw: Now commit this to GitHub
Hub: [Commits and pushes to configured repository]
```

## Features

### Media Generation
- **Multiple providers**: Sora 2 Pro, Kie.ai, extensible to Luma and others
- **Smart routing**: Automatically choose provider based on cost/quality/speed priorities
- **Cost optimization**: Save 70%+ vs always using premium providers
- **Budget controls**: Set spending limits to prevent overruns

### Version Control
- **GitHub integration**: Commit, push, create PRs programmatically
- **GitLab support**: *(coming soon)*
- **Automated workflows**: Combine with media generation for content + commit pipelines

### Data Sources *(coming soon)*
- Google Drive
- Databases
- Cloud storage

## Documentation

- 📚 [Full Documentation](https://github.com/openclaw-community/openclaw-hub-docs)
- 🏗️ [Architecture](https://github.com/openclaw-community/openclaw-hub-docs/blob/main/ARCHITECTURE.md)
- 🔐 [Security Best Practices](https://github.com/openclaw-community/openclaw-hub-docs/blob/main/guides/security-best-practices.md)
- 🛠️ [Adding Providers](https://github.com/openclaw-community/openclaw-hub-docs/blob/main/guides/adding-a-provider.md)

## Project Status

**Current Phase:** MVP Development

See [Milestones](https://github.com/openclaw-community/openclaw-hub/milestones) for roadmap.

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

Good first issues: [Check here](https://github.com/openclaw-community/openclaw-hub/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22)

## Use Cases

### For OpenClaw Users
- Reduce token costs from memory bloat
- Never forget which APIs you have configured
- Automatic cost optimization across providers

### For AI Agent Builders
- Reference implementation for MCP orchestration
- Reusable credential management patterns
- Smart routing algorithms you can adapt

### For Sage (Example)
Sage, an autonomous Instagram bot, uses OpenClaw Hub to:
- Generate pharmaceutical parody videos (Kie.ai for cost)
- Create flagship content (Sora for quality)
- Auto-commit content to GitHub for version control
- Save $400+ annually through intelligent routing

## License

Apache 2.0 - See [LICENSE](LICENSE) for details.

## Community

- 🐛 [Report bugs](https://github.com/openclaw-community/openclaw-hub/issues/new?template=bug_report.md)
- 💡 [Request features](https://github.com/openclaw-community/openclaw-hub/issues/new?template=feature_request.md)
- 💬 [Discussions](https://github.com/openclaw-community/openclaw-hub/discussions)

---

Built with ❤️ by the OpenClaw community
