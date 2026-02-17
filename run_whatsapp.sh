#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# Run the WhatsApp bot (standalone — single command)
#
# Usage:  ./run_whatsapp.sh
#
# This starts the WhatsApp bot with the AI chat service.
# On first run it will show a QR code — scan it with WhatsApp
# (Linked Devices > Link a Device) to pair the bot.
#
# After pairing, messages sent to the bot's WhatsApp number
# will get AI responses, just like the Discord bot.
# ──────────────────────────────────────────────────────────────

set -euo pipefail
cd "$(dirname "$0")/backend"

export PYTHONPATH="$(pwd)"

# Activate nvm if available (needed for Node 20+)
export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
if [ -s "$NVM_DIR/nvm.sh" ]; then
    . "$NVM_DIR/nvm.sh"
    nvm use 20 2>/dev/null || true
fi

# Install WhatsApp bridge node_modules if missing
WA_DIR="icpy/services/whatsapp"
if [ ! -d "$WA_DIR/node_modules" ]; then
    echo "📦 Installing WhatsApp bridge dependencies..."
    (cd "$WA_DIR" && npm install --production)
fi

exec uv run python -m icpy.services.whatsapp.run
