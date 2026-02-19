#!/usr/bin/env bash
# OpenClaw Hub — Uninstaller
#
# Stops the service, backs up .env and aigateway.db, then removes the installation.
# Run from anywhere: ~/.openclaw-hub/scripts/uninstall.sh

set -euo pipefail

OPENCLAW_HUB_HOME="${OPENCLAW_HUB_HOME:-$HOME/.openclaw-hub}"
BACKUP_DIR="$HOME/.openclaw-hub.backup"
MACOS_PLIST_NAME="com.openclaw.hub"
MACOS_PLIST_PATH="$HOME/Library/LaunchAgents/$MACOS_PLIST_NAME.plist"
LINUX_SERVICE_NAME="openclaw-hub"
LINUX_SERVICE_FILE="$HOME/.config/systemd/user/$LINUX_SERVICE_NAME.service"

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

# ── OS Detection ──────────────────────────────────────────────────────────────
detect_os() {
  case "$(uname -s)" in
    Darwin) PLATFORM="macos" ;;
    Linux)  PLATFORM="linux" ;;
    *)      PLATFORM="unknown" ;;
  esac
}

# ── Stop service ──────────────────────────────────────────────────────────────
stop_service() {
  if [ "$PLATFORM" = "macos" ]; then
    if launchctl list 2>/dev/null | grep -q "$MACOS_PLIST_NAME"; then
      info "Stopping and unloading LaunchAgent..."
      launchctl unload "$MACOS_PLIST_PATH" 2>/dev/null || true
      rm -f "$MACOS_PLIST_PATH"
      success "LaunchAgent removed"
    else
      info "No LaunchAgent found to remove"
    fi
  elif [ "$PLATFORM" = "linux" ]; then
    if systemctl --user is-active --quiet "$LINUX_SERVICE_NAME" 2>/dev/null \
       || systemctl --user is-enabled --quiet "$LINUX_SERVICE_NAME" 2>/dev/null; then
      info "Stopping and disabling systemd service..."
      systemctl --user disable --now "$LINUX_SERVICE_NAME" 2>/dev/null || true
      systemctl --user daemon-reload 2>/dev/null || true
      rm -f "$LINUX_SERVICE_FILE"
      success "systemd service removed"
    else
      info "No systemd service found to remove"
    fi
  else
    warn "Unknown platform — skipping service removal"
  fi
}

# ── Backup ────────────────────────────────────────────────────────────────────
backup_data() {
  mkdir -p "$BACKUP_DIR"
  local backed_up=false

  if [ -f "$OPENCLAW_HUB_HOME/.env" ]; then
    cp "$OPENCLAW_HUB_HOME/.env" "$BACKUP_DIR/.env"
    success ".env backed up to $BACKUP_DIR/.env"
    backed_up=true
  fi

  if [ -f "$OPENCLAW_HUB_HOME/aigateway.db" ]; then
    cp "$OPENCLAW_HUB_HOME/aigateway.db" "$BACKUP_DIR/aigateway.db"
    success "Database backed up to $BACKUP_DIR/aigateway.db"
    backed_up=true
  fi

  if [ "$backed_up" = false ]; then
    info "No .env or database found to back up"
  fi
}

# ── Main ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}🦀 OpenClaw Hub — Uninstaller${RESET}"
echo "══════════════════════════════════════════════════════════════"
echo ""

detect_os

# Verify installation exists
if [ ! -d "$OPENCLAW_HUB_HOME" ]; then
  error "No installation found at $OPENCLAW_HUB_HOME"
  exit 1
fi

# Confirm
warn "This will remove OpenClaw Hub from $OPENCLAW_HUB_HOME"
info "Your .env and database will be backed up to $BACKUP_DIR"
echo ""
read -r -p "Continue? [y/N] " confirm
case "$confirm" in
  [yY][eE][sS]|[yY]) ;;
  *)
    info "Uninstall cancelled"
    exit 0
    ;;
esac

echo ""
stop_service
backup_data

info "Removing $OPENCLAW_HUB_HOME ..."
rm -rf "$OPENCLAW_HUB_HOME"
success "Installation removed"

echo ""
echo "══════════════════════════════════════════════════════════════"
echo "  OpenClaw Hub has been uninstalled."
echo ""
echo "  Your configuration and database are preserved at:"
echo "    $BACKUP_DIR"
echo ""
echo "  To reinstall:"
echo "    curl -fsSL https://raw.githubusercontent.com/openclaw-community/openclaw-hub/main/install.sh | bash"
echo "══════════════════════════════════════════════════════════════"
