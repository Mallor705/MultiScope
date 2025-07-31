#!/bin/bash

# Linux-Coop PyInstaller Build Script
# This script compiles the Linux-Coop project into a standalone executable

set -e  # Exit on any error

echo "🚀 Starting Linux-Coop Build Process..."

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Install PyInstaller if not present
if ! pip show pyinstaller >/dev/null 2>&1; then
    echo "📦 Installing PyInstaller..."
    pip install pyinstaller
fi

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build/ dist/ *.spec

# Create PyInstaller spec file
echo "📝 Creating PyInstaller spec file..."
cat > linux-coop.spec << 'EOF'
# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

# Get the project root directory
project_root = Path.cwd()

# Define paths
src_path = project_root / 'src'
styles_path = src_path / 'gui' / 'styles'

# Collect all CSS files and other style resources
css_files = []
if styles_path.exists():
    for css_file in styles_path.glob('*.css'):
        css_files.append((str(css_file), 'src/gui/styles'))

# Collect other resource files if needed
data_files = css_files

# Add hidden imports for PyInstaller
hidden_imports = [
    'gi',
    'gi.repository',
    'gi.repository.Gtk',
    'gi.repository.Adw',
    'gi.repository.Gdk',
    'gi.repository.GLib',
    'gi.repository.Gio',
    'pydantic',
    'psutil',
    'click',
    'cairo'
]

block_cipher = None

a = Analysis(
    ['linuxcoop.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=data_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='linux-coop',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
EOF

# Build with PyInstaller
echo "🔨 Building executable with PyInstaller..."
pyinstaller linux-coop.spec --clean --noconfirm

# Check if build was successful
if [ -f "dist/linux-coop" ]; then
    echo "✅ Build successful!"
    echo "📁 Executable created at: dist/linux-coop"
    echo "📏 File size: $(du -h dist/linux-coop | cut -f1)"

    # Make executable
    chmod +x dist/linux-coop

    echo ""
    echo "🎉 Linux-Coop has been successfully compiled!"
    echo ""
    echo "To run the compiled version:"
    echo "  ./dist/linux-coop"
    echo ""
    echo "To open GUI:"
    echo "  ./dist/linux-coop gui"
    echo ""
    echo "To run a profile:"
    echo "  ./dist/linux-coop <profile_name>"
    echo ""

else
    echo "❌ Build failed! Check the output above for errors."
    exit 1
fi

# Optional: Create a symlink for easier access
if [ ! -L "linux-coop" ]; then
    echo "🔗 Creating symlink for easier access..."
    ln -s dist/linux-coop linux-coop
    echo "   You can now run: ./linux-coop"
fi

echo "✨ Build process complete!"
