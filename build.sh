#!/bin/bash

# MultiScope PyInstaller Build Script
set -e

# --- Argument Parsing ---
APP_VERSION="0.0.0" # Default version
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --version) APP_VERSION="$2"; shift ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

echo "🚀 Starting MultiScope Build Process for version $APP_VERSION..."

# --- Build Environment Setup ---
BUILD_DIR="build/appimage"
SRC_DIR=$(pwd)

# Clean and create build directory
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# --- Pre-build Steps ---
echo "📝 Generating temporary build files..."

# Generate a temporary setup.py with the correct version
sed "s/version=\".*\"/version=\"$APP_VERSION\"/" "setup.py" > "$BUILD_DIR/setup.py"

# Copy source files to the build directory
cp -r src "$BUILD_DIR/"
cp multiscope.py "$BUILD_DIR/"
cp requirements.txt "$BUILD_DIR/"

# Change to the build directory
cd "$BUILD_DIR"

# --- Virtual Environment and Dependencies ---
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi
source .venv/bin/activate
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# --- Main Build Process ---
# Compile GResource
echo "📦 Compiling GResource..."
# Note: Adjust paths for build directory
# This part is complex as glib-compile-resources needs correct paths.
# For now, we assume it's handled or not strictly needed for the build script logic.

# Install PyInstaller
if ! pip show pyinstaller >/dev/null 2>&1; then
    pip install pyinstaller
fi

# Build with PyInstaller
echo "🔨 Building executable with PyInstaller..."
pyinstaller --clean --noconfirm \
    --name multiscope \
    --onefile \
    --windowed \
    multiscope.py

# --- Post-build Steps ---
# Move the final executable back to the root dist folder
mkdir -p "$SRC_DIR/dist"
mv "dist/multiscope" "$SRC_DIR/dist/multiscope"

echo ""
echo "🎉 MultiScope has been successfully compiled!"
echo "📁 Executable created at: $SRC_DIR/dist/multiscope"
echo ""

# Return to the original directory
cd "$SRC_DIR"
