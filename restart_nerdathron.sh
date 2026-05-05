#!/bin/bash
# ══════════════════════════════════════════════════════
#  🌈  restart_nerdathron.sh
#  Kills any running Nerdathron instance and restarts it
#  Put this in ~/Developer/WireFall/
#
#  Apple Shortcut setup:
#    1. Open Shortcuts.app
#    2. New Shortcut → Add Action → "Run Shell Script"
#    3. Paste:  bash ~/Developer/WireFall/restart_nerdathron.sh
#    4. Set "Run as Administrator" toggle ON (for sudo)
#    5. Name it "Restart Firewall" and add to menu bar
# ══════════════════════════════════════════════════════

SCRIPT_DIR="$HOME/Developer/WireFall"
SCRIPT_NAME="nerdathron3001.py"

echo "🔴  Stopping any running Nerdathron instance..."
pkill -f "nerdathron300[01].py" 2>/dev/null
sleep 1

echo "🟢  Starting Nerdathron 3001..."
cd "$SCRIPT_DIR" || { echo "❌  Cannot find $SCRIPT_DIR"; exit 1; }

if [ ! -f "venv/bin/activate" ]; then
    echo "❌  Virtual environment not found in $SCRIPT_DIR/venv"
    echo "    Run: python3 -m venv venv && source venv/bin/activate && pip install PyQt6 psutil openpyxl"
    exit 1
fi

source venv/bin/activate
exec sudo python3 "$SCRIPT_NAME"
