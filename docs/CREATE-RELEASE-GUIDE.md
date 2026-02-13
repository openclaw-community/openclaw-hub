# Creating GitHub Release v1.0.0

## Quick Steps

1. **Go to Releases page:**
   https://github.com/openclaw-community/openclaw-hub/releases/new

2. **Fill in the form:**

   **Choose a tag:** `v1.0.0`
   - Click "Create new tag: v1.0.0 on publish"
   
   **Release title:** `v1.0.0 - Initial Release`
   
   **Description:** (copy this)
   ```markdown
   # AI Gateway v1.0.0 - Initial Release
   
   Production-ready AI orchestration platform with multi-provider LLM support, cost optimization, and workflow orchestration.
   
   ## 🎉 Features
   
   - **Multi-Provider Support**: OpenAI, Anthropic, Ollama (local)
   - **Automatic Routing**: Smart model-based provider selection
   - **Cost Tracking**: Real-time cost calculation and metrics
   - **YAML Workflows**: Human-readable orchestration pipelines
   - **MCP Integration**: External tool support (web search, files, APIs)
   - **OpenAI-Compatible API**: Drop-in replacement for OpenAI SDK
   - **Database Logging**: SQLite storage for all requests
   
   ## 📦 Installation
   
   ```bash
   git clone https://github.com/openclaw-community/openclaw-hub.git
   cd openclaw-hub
   python3.12 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   # Edit .env with your configuration
   uvicorn aigateway.main:app --host 127.0.0.1 --port 8080
   ```
   
   ## 📚 Documentation
   
   - [Quick Start Guide](README.md)
   - [Contributing Guidelines](CONTRIBUTING.md)
   - [MCP Integration Guide](MCP-INTEGRATION.md)
   - [Security Policy](SECURITY.md)
   
   ## 💰 Cost Savings
   
   Smart routing enables up to 97% cost reduction compared to using expensive models for all tasks.
   
   ## 🔗 Links
   
   - [Repository](https://github.com/openclaw-community/openclaw-hub)
   - [Report Issues](https://github.com/openclaw-community/openclaw-hub/issues)
   - [View Documentation](https://github.com/openclaw-community/openclaw-hub/tree/main/docs)
   
   ## 📝 Full Changelog
   
   See [CHANGELOG.md](CHANGELOG.md) for detailed version history.
   
   ## ⚠️ Requirements
   
   - Python 3.12+
   - Ollama (optional, for local models)
   - OpenAI API key (optional)
   - Anthropic API key (optional)
   
   ## 🙏 Credits
   
   Built with FastAPI, SQLAlchemy, and the Model Context Protocol.
   ```

3. **Settings:**
   - ✅ Check "Set as the latest release"
   - ✅ Check "Create a discussion for this release" (if Discussions enabled)

4. **Click "Publish release"**

Done! Your release is now visible at:
https://github.com/openclaw-community/openclaw-hub/releases

## What This Does

- Creates downloadable .zip and .tar.gz files
- Shows up in "Releases" section (no longer says "none")
- Generates a permanent link to this version
- Creates a git tag `v1.0.0`
- Makes project look professional and complete

## Future Releases

When you have updates:

1. Update CHANGELOG.md with new version
2. Create new release (same process, new version number)
3. Follow semantic versioning:
   - v1.0.1 - Bug fixes
   - v1.1.0 - New features (backwards compatible)
   - v2.0.0 - Breaking changes
