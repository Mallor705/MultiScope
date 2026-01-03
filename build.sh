#!/bin/bash

# MultiScope PyInstaller Build Script
# This script compiles the MultiScope project into a standalone executable

set -e  # Exit on any error

./clean.sh

echo "🚀 Starting MultiScope Build Process..."

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

# Compile GResource
echo "📦 Compiling GResource..."
glib-compile-resources \
  --target=res/compiled.gresource \
  --sourcedir=res \
  res/resources.xml

# Install PyInstaller if not present
if ! pip show pyinstaller >/dev/null 2>&1; then
    echo "📦 Installing PyInstaller..."
    pip install pyinstaller
fi

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build/ dist/ *.spec

# Detect system paths for GTK libraries
echo "🔍 Detecting GTK libraries..."
GTK_LIBDIR=$(pkg-config --variable=libdir gtk4 2>/dev/null || echo "/usr/lib/x86_64-linux-gnu")
GI_TYPELIB_PATH=$(pkg-config --variable=typelibdir gobject-introspection-1.0 2>/dev/null || echo "/usr/lib/x86_64-linux-gnu/girepository-1.0")

echo "   GTK Library Path: $GTK_LIBDIR"
echo "   GI Typelib Path: $GI_TYPELIB_PATH"

# Create PyInstaller spec file
echo "📝 Creating PyInstaller spec file..."
cat > multiscope.spec << 'EOF'
# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path
import subprocess

# Get the project root directory
project_root = Path.cwd()

# Define paths
src_path = project_root / 'src'
gui_path = src_path / 'gui'
scripts_path = project_root / 'scripts'

# Collect all CSS files from the res/styles directory
css_files = []
styles_path = project_root / 'res' / 'styles'
if styles_path.exists():
    for css_file in styles_path.glob('*.css'):
        css_files.append((str(css_file), 'res/styles'))

# Collect all JS scripts from the scripts directory
js_files = []
if scripts_path.exists():
    for js_file in scripts_path.glob('*.js'):
        js_files.append((str(js_file), 'scripts'))

# Collect GResource file
gresource_files = []
gresource_file = project_root / 'res' / 'compiled.gresource'
if gresource_file.exists():
    gresource_files.append((str(gresource_file), 'res'))
    print(f"  ✓ Found: {gresource_file}")
else:
    print(f"  ✗ Missing: {gresource_file}")

# Get GObject Introspection typelib path
try:
    gi_typelib_path = subprocess.check_output(
        ['pkg-config', '--variable=typelibdir', 'gobject-introspection-1.0'],
        text=True
    ).strip()
except:
    gi_typelib_path = '/usr/lib/x86_64-linux-gnu/girepository-1.0'

# Collect ALL necessary typelibs
typelib_files = []
required_typelibs = [
    'Gtk-4.0', 'Gsk-4.0', 'Graphene-1.0', 'Adw-1', 'Gdk-4.0',
    'GLib-2.0', 'GObject-2.0', 'Gio-2.0', 'GioUnix-2.0', 'GdkPixbuf-2.0',
    'Pango-1.0', 'PangoCairo-1.0', 'PangoFT2-1.0', 'cairo-1.0',
    'HarfBuzz-0.0', 'freetype2-2.0', 'GModule-2.0', 'xlib-2.0'
]

print(f"Collecting typelibs from: {gi_typelib_path}")
if os.path.exists(gi_typelib_path):
    for typelib in required_typelibs:
        typelib_file = os.path.join(gi_typelib_path, f'{typelib}.typelib')
        if os.path.exists(typelib_file):
            typelib_files.append((typelib_file, 'gi_typelibs'))
            print(f"  ✓ Found: {typelib}")
        else:
            print(f"  ✗ Missing: {typelib}")

# Collect GTK/GDK shared libraries
binaries = []
try:
    gtk_libdir = subprocess.check_output(
        ['pkg-config', '--variable=libdir', 'gtk4'],
        text=True
    ).strip()

    # Critical GTK4 libraries
    gtk_libs = [
        'libgtk-4.so.1',
        'libadwaita-1.so.0',
        'libgdk_pixbuf-2.0.so.0',
        'libpango-1.0.so.0',
        'libpangocairo-1.0.so.0',
        'libcairo.so.2',
        'libcairo-gobject.so.2',
        'libharfbuzz.so.0',
        'libgraphene-1.0.so.0',
        'libepoxy.so.0',
        'libEGL.so.1',
        'libGLX.so.0',
        'libGL.so.1',
        'libGLdispatch.so.0',
        'libdrm.so.2',
        'libgbm.so.1'
    ]

    for lib in gtk_libs:
        lib_path = os.path.join(gtk_libdir, lib)
        if os.path.exists(lib_path):
            binaries.append((lib_path, '.'))
            print(f"  ✓ Including library: {lib}")
except:
    print("Warning: Could not detect GTK library path")

# Collect other resource files
data_files = css_files + js_files + gresource_files + typelib_files

# Add hidden imports for PyInstaller
hidden_imports = [
    'gi',
    'gi.repository',
    'gi.repository.Gtk',
    'gi.repository.Gsk',
    'gi.repository.Graphene',
    'gi.repository.Adw',
    'gi.repository.Gdk',
    'gi.repository.GLib',
    'gi.repository.Gio',
    'gi.repository.GObject',
    'gi.repository.GdkPixbuf',
    'gi.repository.Pango',
    'gi.repository.PangoCairo',
    'gi.repository.PangoFT2',
    'pydantic',
    'cairo',
    'evdev',
    'pydbus',
    'screeninfo'
]

block_cipher = None

a = Analysis(
    ['multiscope.py'],
    pathex=[str(project_root)],
    binaries=binaries,
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
    name='multiscope',
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
pyinstaller multiscope.spec --clean --noconfirm

# Check if build was successful
if [ -f "dist/multiscope" ]; then
    echo "✅ Build successful!"
    echo "📁 Executable created at: dist/multiscope"
    echo "📏 File size: $(du -h dist/multiscope | cut -f1)"

    # Make executable
    chmod +x dist/multiscope

    echo ""
    echo "🎉 MultiScope has been successfully compiled!"
    echo ""
    echo "To run the compiled version:"
    echo "  ./dist/multiscope"
    echo ""
    echo "To open GUI:"
    echo "  ./dist/multiscope gui"
    echo ""
    echo "To run a profile:"
    echo "  ./dist/multiscope <profile_name>"
    echo ""

else
    echo "❌ Build failed! Check the output above for errors."
    exit 1
fi
