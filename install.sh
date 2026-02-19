#!/usr/bin/env bash
# OpenClaw Hub — Unified One-Line Installer
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/openclaw-community/openclaw-hub/main/install.sh | bash
#
# Environment overrides:
#   OPENCLAW_HUB_HOME   Install location (default: ~/.openclaw-hub)
#   HUB_HOST            Bind address      (default: 127.0.0.1)
#   HUB_PORT            Port              (default: 8080)

set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
REPO_URL="https://github.com/openclaw-community/openclaw-hub.git"
OPENCLAW_HUB_HOME="${OPENCLAW_HUB_HOME:-$HOME/.openclaw-hub}"
HUB_HOST="${HUB_HOST:-127.0.0.1}"
HUB_PORT="${HUB_PORT:-8080}"
MIN_PYTHON_MAJOR=3
MIN_PYTHON_MINOR=12
HEALTH_TIMEOUT=30

# Platform-specific service identifiers (keep consistent with existing installations)
MACOS_PLIST_NAME="com.openclaw.hub"
MACOS_PLIST_PATH="$HOME/Library/LaunchAgents/$MACOS_PLIST_NAME.plist"
LINUX_SERVICE_NAME="openclaw-hub"
LINUX_SERVICE_FILE="$HOME/.config/systemd/user/$LINUX_SERVICE_NAME.service"

# Runtime state
PLATFORM=""
PYTHON=""
UPDATE_MODE=false

# ── Colours ───────────────────────────────────────────────────────────────────
if [[ -t 1 ]]; then
  RED="\033[0;31m"; GREEN="\033[0;32m"; YELLOW="\033[0;33m"
  CYAN="\033[0;36m"; BOLD="\033[1m"; RESET="\033[0m"
else
  RED=""; GREEN=""; YELLOW=""; CYAN=""; BOLD=""; RESET=""
fi

info()    { echo -e "${CYAN}ℹ${RESET}  $*"; }
success() { echo -e "${GREEN}✓${RESET}  $*"; }
warn()    { echo -e "${YELLOW}⚠${RESET}  $*"; }
error()   { echo -e "${RED}✗${RESET}  $*" >&2; }
die()     { error "$*"; exit 1; }
header()  { echo -e "\n${BOLD}── $* ──${RESET}"; }

# ── Phase 1: OS Detection ────────────────────────────────────────────────────
detect_os() {
  local os
  os="$(uname -s)"
  case "$os" in
    Darwin) PLATFORM="macos" ;;
    Linux)  PLATFORM="linux" ;;
    *)
      die "Unsupported OS: $os\n   OpenClaw Hub supports macOS and Linux.\n   Windows users: please use WSL2 — https://docs.openclaw.ai/install/wsl2"
      ;;
  esac
}

# ── Phase 1: Preflight Checks ────────────────────────────────────────────────
check_git() {
  if ! command -v git &>/dev/null; then
    error "git is required but not installed."
    if [ "$PLATFORM" = "macos" ]; then
      info "Install with:  brew install git"
      info "Or via Xcode:  xcode-select --install"
    else
      info "Install with:  sudo apt install git   (Debian/Ubuntu)"
      info "           or: sudo yum install git   (RHEL/CentOS)"
    fi
    exit 1
  fi
  success "git $(git --version | awk '{print $3}')"
}

find_python() {
  for candidate in python3.12 python3.13 python3.14 python3 python; do
    if command -v "$candidate" &>/dev/null; then
      local ver major minor
      ver="$("$candidate" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)" || continue
      major="${ver%%.*}"
      minor="${ver##*.}"
      if [[ "$major" -ge "$MIN_PYTHON_MAJOR" && "$minor" -ge "$MIN_PYTHON_MINOR" ]]; then
        PYTHON="$candidate"
        success "Python $ver ($("$candidate" -c "import sys; print(sys.executable)"))"
        return 0
      fi
    fi
  done

  error "Python $MIN_PYTHON_MAJOR.$MIN_PYTHON_MINOR+ is required but not found."
  if [ "$PLATFORM" = "macos" ]; then
    info "Install with:  brew install python@3.12"
  else
    info "Install with:  sudo apt install python3.12 python3.12-venv   (Debian/Ubuntu)"
    info "Or via PPA:    sudo add-apt-repository ppa:deadsnakes/ppa && sudo apt install python3.12 python3.12-venv"
  fi
  exit 1
}

preflight() {
  header "Phase 1: Preflight Checks"
  check_git
  find_python
}

# ── Phase 2: Download & Environment Setup ────────────────────────────────────
stop_service() {
  if [ "$PLATFORM" = "macos" ]; then
    if launchctl list 2>/dev/null | grep -q "$MACOS_PLIST_NAME"; then
      info "Stopping existing service..."
      launchctl unload "$MACOS_PLIST_PATH" 2>/dev/null || true
    fi
  else
    if systemctl --user is-active --quiet "$LINUX_SERVICE_NAME" 2>/dev/null; then
      info "Stopping existing service..."
      systemctl --user stop "$LINUX_SERVICE_NAME" 2>/dev/null || true
    fi
  fi
}

setup_environment() {
  header "Phase 2: Download & Environment Setup"

  if [ -d "$OPENCLAW_HUB_HOME/.git" ]; then
    warn "Existing installation found at $OPENCLAW_HUB_HOME — switching to update mode"
    UPDATE_MODE=true
  fi

  if [ "$UPDATE_MODE" = true ]; then
    stop_service
    cd "$OPENCLAW_HUB_HOME"
    info "Pulling latest changes from main..."
    git pull origin main
  else
    info "Cloning to $OPENCLAW_HUB_HOME ..."
    git clone "$REPO_URL" "$OPENCLAW_HUB_HOME"
    cd "$OPENCLAW_HUB_HOME"
  fi

  info "Creating Python virtual environment..."
  "$PYTHON" -m venv venv
  success "Virtual environment ready"

  info "Installing/updating dependencies..."
  venv/bin/pip install --quiet --upgrade pip
  venv/bin/pip install --quiet -r requirements.txt
  success "Dependencies installed"

  if [ ! -f ".env" ]; then
    cp .env.example .env
    success ".env created from .env.example"
    _bootstrap_env
  else
    info ".env already exists — preserving your configuration"
    # Still ensure a secret key exists on updates
    _ensure_secret_key
  fi
}

_bootstrap_env() {
  local secret
  secret=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null \
           || openssl rand -hex 32 2>/dev/null \
           || date +%s%N | sha256sum | head -c 64)

  # Set/update DASHBOARD_SECRET_KEY
  _set_env "DASHBOARD_SECRET_KEY" "$secret"
  # Ensure HOST and PORT are present
  grep -q "^HOST=" .env 2>/dev/null || echo "HOST=$HUB_HOST" >> .env
  grep -q "^PORT=" .env 2>/dev/null || echo "PORT=$HUB_PORT" >> .env

  success "Bootstrap configuration written to .env"
}

_ensure_secret_key() {
  if ! grep -q "^DASHBOARD_SECRET_KEY=.\+" .env 2>/dev/null; then
    local secret
    secret=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null \
             || openssl rand -hex 32 2>/dev/null \
             || date +%s%N | sha256sum | head -c 64)
    _set_env "DASHBOARD_SECRET_KEY" "$secret"
    info "Generated missing DASHBOARD_SECRET_KEY"
  fi
}

_set_env() {
  # Portable sed: update key=value in .env (macOS needs '' after -i)
  local key="$1" val="$2"
  if grep -q "^${key}=" .env 2>/dev/null; then
    if [ "$PLATFORM" = "macos" ]; then
      sed -i '' "s|^${key}=.*|${key}=${val}|" .env
    else
      sed -i "s|^${key}=.*|${key}=${val}|" .env
    fi
  else
    echo "${key}=${val}" >> .env
  fi
}

# ── Phase 3: Minimal Bootstrap Config ────────────────────────────────────────
detect_ollama() {
  header "Phase 3: Bootstrap Configuration"
  if curl -s --max-time 2 "http://127.0.0.1:11434/api/tags" &>/dev/null; then
    success "Local Ollama detected — Hub will route local model requests immediately"
  else
    info "No local Ollama detected — configure AI providers in the dashboard after install"
  fi
}

# ── Phase 4: Service Installation ────────────────────────────────────────────
install_macos() {
  local venv_uvicorn="$OPENCLAW_HUB_HOME/venv/bin/uvicorn"
  local log_path="$OPENCLAW_HUB_HOME/hub.log"

  mkdir -p "$HOME/Library/LaunchAgents"

  info "Writing LaunchAgent plist: $MACOS_PLIST_PATH"
  cat > "$MACOS_PLIST_PATH" << PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${MACOS_PLIST_NAME}</string>

    <key>ProgramArguments</key>
    <array>
        <string>${venv_uvicorn}</string>
        <string>aigateway.main:app</string>
        <string>--host</string>
        <string>${HUB_HOST}</string>
        <string>--port</string>
        <string>${HUB_PORT}</string>
    </array>

    <key>WorkingDirectory</key>
    <string>${OPENCLAW_HUB_HOME}</string>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>${log_path}</string>

    <key>StandardErrorPath</key>
    <string>${log_path}</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin</string>
        <key>OPENCLAW_SERVICE_MANAGER</key>
        <string>launchd</string>
    </dict>
</dict>
</plist>
PLIST_EOF

  info "Loading service..."
  launchctl load "$MACOS_PLIST_PATH"
  success "macOS LaunchAgent installed and loaded"
}

install_linux() {
  local venv_uvicorn="$OPENCLAW_HUB_HOME/venv/bin/uvicorn"
  local log_path="$OPENCLAW_HUB_HOME/hub.log"

  mkdir -p "$HOME/.config/systemd/user"

  info "Writing systemd unit: $LINUX_SERVICE_FILE"
  cat > "$LINUX_SERVICE_FILE" << SERVICE_EOF
[Unit]
Description=OpenClaw Hub — AI Gateway
After=network.target

[Service]
Type=simple
WorkingDirectory=${OPENCLAW_HUB_HOME}
ExecStart=${venv_uvicorn} aigateway.main:app --host ${HUB_HOST} --port ${HUB_PORT}
Restart=always
RestartSec=10
StandardOutput=append:${log_path}
StandardError=append:${log_path}
Environment=OPENCLAW_SERVICE_MANAGER=systemd

[Install]
WantedBy=default.target
SERVICE_EOF

  info "Enabling and starting systemd user service..."
  systemctl --user daemon-reload
  systemctl --user enable "$LINUX_SERVICE_NAME"
  systemctl --user start "$LINUX_SERVICE_NAME"
  success "systemd user service installed and started"
}

install_service() {
  header "Phase 4: Service Installation"
  if [ "$PLATFORM" = "macos" ]; then
    install_macos
  else
    install_linux
  fi
}

# ── Health Check ─────────────────────────────────────────────────────────────
wait_for_health() {
  header "Phase 5: Health Check"
  info "Polling http://$HUB_HOST:$HUB_PORT/health (timeout: ${HEALTH_TIMEOUT}s)..."
  local elapsed=0
  while [ "$elapsed" -lt "$HEALTH_TIMEOUT" ]; do
    if curl -s --max-time 2 "http://$HUB_HOST:$HUB_PORT/health" &>/dev/null; then
      echo ""
      success "Hub is healthy"
      return 0
    fi
    printf "."
    sleep 2
    elapsed=$((elapsed + 2))
  done
  echo ""
  error "Hub did not respond within ${HEALTH_TIMEOUT}s"
  _print_diagnostics
  exit 1
}

_print_diagnostics() {
  warn "Diagnostic information:"
  if [ "$PLATFORM" = "macos" ]; then
    echo "  Service status:"
    launchctl list 2>/dev/null | grep "$MACOS_PLIST_NAME" || echo "    (not listed)"
    echo "  Last 20 log lines (hub.log):"
    tail -20 "$OPENCLAW_HUB_HOME/hub.log" 2>/dev/null || echo "    (log not found)"
  else
    echo "  Service status:"
    systemctl --user status "$LINUX_SERVICE_NAME" --no-pager 2>/dev/null || echo "    (not found)"
    echo "  Last 20 log entries:"
    journalctl --user -u "$LINUX_SERVICE_NAME" -n 20 --no-pager 2>/dev/null \
      || tail -20 "$OPENCLAW_HUB_HOME/hub.log" 2>/dev/null \
      || echo "    (no logs available)"
  fi
}

# ── Phase 5: Handoff ─────────────────────────────────────────────────────────
print_success_banner() {
  local stop_cmd start_cmd logs_cmd

  if [ "$PLATFORM" = "macos" ]; then
    stop_cmd="launchctl unload ~/Library/LaunchAgents/${MACOS_PLIST_NAME}.plist"
    start_cmd="launchctl load  ~/Library/LaunchAgents/${MACOS_PLIST_NAME}.plist"
    logs_cmd="tail -f ~/.openclaw-hub/hub.log"
  else
    stop_cmd="systemctl --user stop ${LINUX_SERVICE_NAME}"
    start_cmd="systemctl --user start ${LINUX_SERVICE_NAME}"
    logs_cmd="journalctl --user -u ${LINUX_SERVICE_NAME} -f"
  fi

  local mode_msg=""
  if [ "$UPDATE_MODE" = true ]; then
    mode_msg=" (updated)"
  fi

  echo ""
  echo "══════════════════════════════════════════════════════════════"
  echo "  ✓ OpenClaw Hub is running${mode_msg}!"
  echo ""
  echo "  Dashboard:  http://${HUB_HOST}:${HUB_PORT}/dashboard"
  echo "  API Docs:   http://${HUB_HOST}:${HUB_PORT}/docs"
  echo "  Health:     http://${HUB_HOST}:${HUB_PORT}/health"
  echo ""
  echo "  Next step:  Open the dashboard to configure your"
  echo "              AI provider connections and API keys."
  echo ""
  echo "  Manage the service:"
  echo "    Stop:    ${stop_cmd}"
  echo "    Start:   ${start_cmd}"
  echo "    Logs:    ${logs_cmd}"
  echo ""
  echo "  Update:     curl -fsSL https://raw.githubusercontent.com/openclaw-community/openclaw-hub/main/install.sh | bash"
  echo "  Uninstall:  ~/.openclaw-hub/scripts/uninstall.sh"
  echo "══════════════════════════════════════════════════════════════"
}

open_browser() {
  local url="http://${HUB_HOST}:${HUB_PORT}/dashboard"
  if [ "$PLATFORM" = "macos" ]; then
    open "$url" 2>/dev/null || true
  else
    # Best-effort: silently skip if headless / no display server
    xdg-open "$url" 2>/dev/null || true
  fi
}

# ── Main ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}🦀 OpenClaw Hub — Installer${RESET}"
echo "══════════════════════════════════════════════════════════════"

detect_os
preflight
setup_environment
detect_ollama
install_service
wait_for_health
print_success_banner
open_browser
