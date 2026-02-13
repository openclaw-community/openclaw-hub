# Installation Guide

OpenClaw Hub can run as a standalone server or be installed as a system service for automatic startup.

## Prerequisites

- Python 3.12 or higher
- Git (for cloning the repository)
- API keys for providers you want to use (optional - Ollama works without keys)

## Basic Installation

### 1. Clone Repository

```bash
git clone https://github.com/openclaw-community/openclaw-hub.git
cd openclaw-hub
```

### 2. Create Virtual Environment

```bash
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your API keys (optional)
```

### 5. Test Run

```bash
uvicorn aigateway.main:app --host 127.0.0.1 --port 8080 --reload
```

Visit http://127.0.0.1:8080/docs to verify it's working.

---

## Auto-Start Installation (Recommended)

For production use, install OpenClaw Hub as a system service so it starts automatically on boot.

### macOS (LaunchAgent)

Run the installation script:

```bash
./install-macos.sh
```

**Manual Installation:**

1. Copy the LaunchAgent plist to your user's LaunchAgents directory
2. Load the service:

```bash
launchctl load ~/Library/LaunchAgents/com.openclaw.hub.plist
```

**Management Commands:**

```bash
# Start
launchctl load ~/Library/LaunchAgents/com.openclaw.hub.plist

# Stop
launchctl unload ~/Library/LaunchAgents/com.openclaw.hub.plist

# Restart
launchctl unload ~/Library/LaunchAgents/com.openclaw.hub.plist && \
launchctl load ~/Library/LaunchAgents/com.openclaw.hub.plist

# Check status
launchctl list | grep openclaw.hub

# View logs
tail -f gateway.log
```

### Linux (systemd)

Run the installation script:

```bash
./install-linux.sh
```

**Manual Installation:**

1. Create systemd user service file: `~/.config/systemd/user/openclaw-hub.service`
2. Enable and start:

```bash
systemctl --user daemon-reload
systemctl --user enable openclaw-hub
systemctl --user start openclaw-hub
```

**Management Commands:**

```bash
# Start
systemctl --user start openclaw-hub

# Stop
systemctl --user stop openclaw-hub

# Restart
systemctl --user restart openclaw-hub

# Check status
systemctl --user status openclaw-hub

# View logs
journalctl --user -u openclaw-hub -f
# or
tail -f gateway.log

# Disable auto-start
systemctl --user disable openclaw-hub
```

### Windows (Task Scheduler)

**Option 1: Using Task Scheduler GUI**

1. Open Task Scheduler (`taskschd.msc`)
2. Create Basic Task:
   - **Name:** OpenClaw Hub
   - **Trigger:** At log on
   - **Action:** Start a program
   - **Program:** `C:\Path\To\openclaw-hub\venv\Scripts\python.exe`
   - **Arguments:** `-m uvicorn aigateway.main:app --host 127.0.0.1 --port 8080`
   - **Start in:** `C:\Path\To\openclaw-hub`
3. Edit task properties:
   - Check "Run whether user is logged on or not"
   - Check "Run with highest privileges" (if needed)
   - Under Conditions, uncheck "Start the task only if the computer is on AC power"

**Option 2: PowerShell Script**

Create `start-hub.ps1`:

```powershell
# OpenClaw Hub Startup Script
$hubPath = "C:\Path\To\openclaw-hub"
$pythonExe = "$hubPath\venv\Scripts\python.exe"
$logFile = "$hubPath\gateway.log"

Set-Location $hubPath
Start-Process -FilePath $pythonExe `
    -ArgumentList "-m", "uvicorn", "aigateway.main:app", "--host", "127.0.0.1", "--port", "8080" `
    -RedirectStandardOutput $logFile `
    -RedirectStandardError $logFile `
    -WindowStyle Hidden
```

Then create a scheduled task that runs this script at startup.

**Option 3: NSSM (Non-Sucking Service Manager)**

1. Download [NSSM](https://nssm.cc/download)
2. Install as Windows service:

```cmd
nssm install OpenClawHub "C:\Path\To\openclaw-hub\venv\Scripts\python.exe"
nssm set OpenClawHub AppParameters "-m uvicorn aigateway.main:app --host 127.0.0.1 --port 8080"
nssm set OpenClawHub AppDirectory "C:\Path\To\openclaw-hub"
nssm set OpenClawHub AppStdout "C:\Path\To\openclaw-hub\gateway.log"
nssm set OpenClawHub AppStderr "C:\Path\To\openclaw-hub\gateway.log"
nssm start OpenClawHub
```

**Management:**

```cmd
# Start
nssm start OpenClawHub

# Stop
nssm stop OpenClawHub

# Restart
nssm restart OpenClawHub

# Status
nssm status OpenClawHub

# Remove
nssm remove OpenClawHub confirm
```

---

## Verification

After installation, verify the Hub is running:

```bash
# Health check
curl http://127.0.0.1:8080/health

# List available models
curl http://127.0.0.1:8080/v1/models

# View interactive docs
open http://127.0.0.1:8080/docs  # macOS
xdg-open http://127.0.0.1:8080/docs  # Linux
start http://127.0.0.1:8080/docs  # Windows
```

---

## Troubleshooting

### Service won't start

1. Check logs:
   - macOS: `tail -f ~/path/to/openclaw-hub/gateway.log`
   - Linux: `journalctl --user -u openclaw-hub -n 50`
   - Windows: Check `gateway.log` in the Hub directory

2. Verify Python environment:
   ```bash
   source venv/bin/activate
   python --version  # Should be 3.12+
   pip list | grep fastapi  # Should show fastapi installed
   ```

3. Test manual start:
   ```bash
   cd /path/to/openclaw-hub
   source venv/bin/activate
   uvicorn aigateway.main:app --host 127.0.0.1 --port 8080
   ```

### Port already in use

If port 8080 is already in use, you can change it:

1. Edit your service configuration (plist/systemd/Task Scheduler)
2. Change `--port 8080` to another port (e.g., `--port 8081`)
3. Reload/restart the service
4. Update any clients to use the new port

### Permission issues

- **macOS:** Ensure the plist file is in `~/Library/LaunchAgents/` (not `/Library/LaunchAgents/`)
- **Linux:** Use `--user` flag with systemctl (not sudo)
- **Windows:** Run Task Scheduler or NSSM as Administrator

---

## Updating

To update OpenClaw Hub:

```bash
# Stop the service first
# macOS: launchctl unload ~/Library/LaunchAgents/com.openclaw.hub.plist
# Linux: systemctl --user stop openclaw-hub

# Pull latest code
cd /path/to/openclaw-hub
git pull

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Restart service
# macOS: launchctl load ~/Library/LaunchAgents/com.openclaw.hub.plist
# Linux: systemctl --user start openclaw-hub
```

---

## Uninstalling

### macOS

```bash
launchctl unload ~/Library/LaunchAgents/com.openclaw.hub.plist
rm ~/Library/LaunchAgents/com.openclaw.hub.plist
```

### Linux

```bash
systemctl --user stop openclaw-hub
systemctl --user disable openclaw-hub
rm ~/.config/systemd/user/openclaw-hub.service
systemctl --user daemon-reload
```

### Windows (NSSM)

```cmd
nssm stop OpenClawHub
nssm remove OpenClawHub confirm
```

Then delete the openclaw-hub directory.

---

## Next Steps

- Read the [AI Agent Discovery Guide](AI-AGENT-DISCOVERY.md) to learn how to use the Hub
- Check out [example workflows](../pipelines/) for orchestration
- Review [GitHub Integration](../GITHUB-INTEGRATION.md) for repository access
- Join the community: https://discord.com/invite/clawd
