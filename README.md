# PulseWave - Audio Visualizer & Video Studio (macOS)

PulseWave is a native desktop application for macOS that lets you drop in any audio file (MP3, WAV, FLAC, M4A, OGG), analyzes its waveform and frequency spectrum, renders real-time audio visualizers (Circular Spectrum, Neon Equalizer Bars, Waveform Oscilloscope, Cyber Horizon, Galaxy Nebula), and exports high-quality 60fps MP4 videos with synchronized audio.

Packaged ready for **PyInstaller** as a standalone macOS **`PulseWave.app`** bundle!

---

## ⚡ Option 1: Instant Launch (Run in 2 seconds)

To run the app immediately with Python:

```bash
bash run_app.sh
```

*(This automatically creates a virtual environment, installs dependencies, and launches the app!)*

---

## 📦 Option 2: Build Standalone macOS App (`PulseWave.app`) with PyInstaller

To compile a native macOS `.app` bundle:

```bash
bash build_macos_app.sh
```

*(Or `chmod +x build_macos_app.sh && ./build_macos_app.sh`)*

Once compiled, your standalone application will be in:
```
dist/PulseWave.app
```

To test run:
```bash
open dist/PulseWave.app
```

To install to your Mac's Applications:
```bash
cp -R dist/PulseWave.app /Applications/
```

---

## ⚠️ Terminal Command Note
If you previously ran `chmod +x build_macos_app.sh ./build_macos_app.sh` on a single line without a separator, `chmod` treated `./build_macos_app.sh` as a file to mark executable, rather than running it! Run either:
```bash
bash build_macos_app.sh
```
or
```bash
./build_macos_app.sh
```
