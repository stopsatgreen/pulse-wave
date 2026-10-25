#!/usr/bin/env bash
# ==============================================================================
# PulseWave - Instant Launcher (Runs Python GUI directly without PyInstaller)
# ==============================================================================

set -e

echo ""
echo "🚀 Launching PulseWave Python Desktop Studio..."

# 1. Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 not found. Install it via https://python.org or 'brew install python'"
    exit 1
fi

# 2. Check virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment and installing dependencies..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# 3. Launch the application
echo "🎵 Starting PulseWave..."
python3 main.py
