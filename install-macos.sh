#!/usr/bin/env bash
# ⚠️  This script has been superseded by the unified installer.
#
# Please use:
#   curl -fsSL https://raw.githubusercontent.com/openclaw-community/openclaw-hub/main/install.sh | bash
#
# Or, if you have the repo cloned already:
#   bash install.sh

set -e

echo ""
echo "⚠️  install-macos.sh is deprecated."
echo ""
echo "   Please use the unified installer instead:"
echo "   curl -fsSL https://raw.githubusercontent.com/openclaw-community/openclaw-hub/main/install.sh | bash"
echo ""
echo "   Redirecting to install.sh now..."
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$SCRIPT_DIR/install.sh" "$@"
