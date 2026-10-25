# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Specification for PulseWave macOS .app Bundle
Run with: pyinstaller AudioVisualizer.spec --noconfirm --clean
"""

import sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'scipy',
        'scipy.io',
        'scipy.io.wavfile',
        'numpy',
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'pandas', 'IPython', 'notebook'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PulseWave',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PulseWave',
)

app = BUNDLE(
    coll,
    name='PulseWave.app',
    icon=None,
    bundle_identifier='com.pulsewave.audiovisualizer',
    info_plist={
        'CFBundleName': 'PulseWave',
        'CFBundleDisplayName': 'PulseWave Audio Visualizer',
        'CFBundleIdentifier': 'com.pulsewave.audiovisualizer',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': 'True',
        'LSMinimumSystemVersion': '11.0.0',
        'NSHumanReadableCopyright': 'Copyright (c) 2026 PulseWave',
    },
)
