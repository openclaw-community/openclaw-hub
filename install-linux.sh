#!/bin/bash
# OpenClaw Hub - Linux Installation Script
# Installs Hub as a systemd service for automatic startup

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="openclaw-hub"
SERVICE_PATH="$HOME/.config/systemd/user/$SERVICE_NAME.service"
VENV_UVICORN="$SCRIPT_DIR/venv/bin/uvicorn"
LOG_PATH="$SCRIPT_DIR/gateway.log"

echo "🦀 OpenClaw Hub - Linux Installation"
echo "====================================="
echo ""

# Check if virtual environment exists
if [ ! -f "$VENV_UVICORN" ]; then
    echo "❌ Error: Virtual environment not found at $SCRIPT_DIR/venv"
    echo "   Please run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Create systemd user directory if it doesn't exist
mkdir -p "$HOME/.config/systemd/user"

# Stop existing service if running
if systemctl --user is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
    echo "⏸️  Stopping existing service..."
    systemctl --user stop "$SERVICE_NAME"
fi

# Create systemd service file
echo "📝 Creating systemd service configuration..."
cat > "$SERVICE_PATH" << EOF
[Unit]
Description=OpenClaw Hub - AI Gateway
After=network.target

[Service]
Type=simple
WorkingDirectory=$SCRIPT_DIR
ExecStart=$VENV_UVICORN aigateway.main:app --host 127.0.0.1 --port 8080
Restart=always
RestartSec=10
StandardOutput=append:$LOG_PATH
StandardError=append:$LOG_PATH

[Install]
WantedBy=default.target
EOF

# Reload systemd and enable service
echo "🚀 Enabling service..."
systemctl --user daemon-reload
systemctl --user enable "$SERVICE_NAME"
systemctl --user start "$SERVICE_NAME"

# Wait for startup
echo "⏳ Waiting for Hub to start..."
sleep 3

# Test the service
if curl -s --max-time 2 http://127.0.0.1:8080/health > /dev/null 2>&1; then
    echo ""
    echo "✅ OpenClaw Hub installed successfully!"
    echo ""
    echo "Service Status:"
    systemctl --user status "$SERVICE_NAME" --no-pager -l
    echo ""
    echo "📊 Dashboard: http://127.0.0.1:8080/docs"
    echo "📝 Logs:      journalctl --user -u $SERVICE_NAME -f"
    echo "             (or tail -f $LOG_PATH)"
    echo ""
    echo "The Hub will now start automatically on system boot."
    echo ""
    echo "Commands:"
    echo "  Start:   systemctl --user start $SERVICE_NAME"
    echo "  Stop:    systemctl --user stop $SERVICE_NAME"
    echo "  Restart: systemctl --user restart $SERVICE_NAME"
    echo "  Status:  systemctl --user status $SERVICE_NAME"
    echo "  Disable: systemctl --user disable $SERVICE_NAME"
else
    echo ""
    echo "⚠️  Service installed but health check failed."
    echo "   Check logs: journalctl --user -u $SERVICE_NAME -n 50"
    exit 1
fi
