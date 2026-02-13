#!/bin/bash
# OpenClaw Hub - macOS Installation Script
# Installs Hub as a LaunchAgent for automatic startup

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST_NAME="com.openclaw.hub"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME.plist"
VENV_UVICORN="$SCRIPT_DIR/venv/bin/uvicorn"
LOG_PATH="$SCRIPT_DIR/gateway.log"

echo "🦀 OpenClaw Hub - macOS Installation"
echo "======================================"
echo ""

# Check if virtual environment exists
if [ ! -f "$VENV_UVICORN" ]; then
    echo "❌ Error: Virtual environment not found at $SCRIPT_DIR/venv"
    echo "   Please run: python3.12 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Stop existing service if running
if launchctl list | grep -q "$PLIST_NAME"; then
    echo "⏸️  Stopping existing service..."
    launchctl unload "$PLIST_PATH" 2>/dev/null || true
fi

# Create LaunchAgent plist
echo "📝 Creating LaunchAgent configuration..."
cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$PLIST_NAME</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>$VENV_UVICORN</string>
        <string>aigateway.main:app</string>
        <string>--host</string>
        <string>127.0.0.1</string>
        <string>--port</string>
        <string>8080</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>$SCRIPT_DIR</string>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <true/>
    
    <key>StandardOutPath</key>
    <string>$LOG_PATH</string>
    
    <key>StandardErrorPath</key>
    <string>$LOG_PATH</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin</string>
    </dict>
</dict>
</plist>
EOF

# Load the service
echo "🚀 Loading service..."
launchctl load "$PLIST_PATH"

# Wait for startup
echo "⏳ Waiting for Hub to start..."
sleep 3

# Test the service
if curl -s --max-time 2 http://127.0.0.1:8080/health > /dev/null 2>&1; then
    echo ""
    echo "✅ OpenClaw Hub installed successfully!"
    echo ""
    echo "Service Status:"
    launchctl list | grep openclaw.hub || echo "  (service loaded)"
    echo ""
    echo "📊 Dashboard: http://127.0.0.1:8080/docs"
    echo "📝 Logs:      tail -f $LOG_PATH"
    echo ""
    echo "The Hub will now start automatically on system boot."
    echo ""
    echo "Commands:"
    echo "  Start:   launchctl load ~/Library/LaunchAgents/$PLIST_NAME.plist"
    echo "  Stop:    launchctl unload ~/Library/LaunchAgents/$PLIST_NAME.plist"
    echo "  Restart: launchctl unload ~/Library/LaunchAgents/$PLIST_NAME.plist && launchctl load ~/Library/LaunchAgents/$PLIST_NAME.plist"
else
    echo ""
    echo "⚠️  Service installed but health check failed."
    echo "   Check logs: tail -f $LOG_PATH"
    exit 1
fi
