#!/usr/bin/env bash
# ==============================================================================
# PulseWave - Audio Visualizer & Video Studio
# One-Click macOS PyInstaller Build Script
# ==============================================================================

set -e

echo ""
echo "============================================================"
echo "  PulseWave macOS PyInstaller Builder"
echo "============================================================"
echo ""

# 1. Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 was not found on your system."
    echo "Please install Python 3 via python.org or Homebrew (brew install python)."
    exit 1
fi

# 2. Check for FFmpeg (Required for MP4 encoding & audio decoding)
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️ Warning: ffmpeg was not detected in PATH."
    echo "On macOS, install it simply via: brew install ffmpeg"
fi

# 3. Create Virtual Environment
echo "📦 1. Setting up Python virtual environment (venv)..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

# 4. Install Dependencies
echo "⬇️ 2. Installing required dependencies from requirements.txt..."
pip install --upgrade pip
pip install -r requirements.txt

# 5. Build with PyInstaller
echo "🔨 3. Compiling macOS Application Bundle (.app) with PyInstaller..."
PYINSTALLER_CONFIG_DIR="$(pwd)/.pyinstaller_cache" pyinstaller AudioVisualizer.spec --noconfirm

# 6. Verify Output
if [ -d "dist/PulseWave.app" ]; then
    echo ""
    echo "============================================================"
    echo "  🎉 BUILD SUCCESSFUL!"
    echo "============================================================"
    echo ""
    echo "Your macOS app bundle is ready at:"
    echo "  📍 $(pwd)/dist/PulseWave.app"
    echo ""
    echo "To test run your app immediately:"
    echo "  open dist/PulseWave.app"
    echo ""
    echo "To install to your Applications folder:"
    echo "  cp -R dist/PulseWave.app /Applications/"
    echo ""
else
    echo "❌ Build finished but dist/PulseWave.app was not found."
    exit 1
fi
