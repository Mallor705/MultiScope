#!/bin/bash

set -e # Exit on any error

# --- Versioning Setup ---
echo "🚀 Starting versioning process..."

# Get version from Git tag
if GIT_TAG=$(git describe --tags --abbrev=0 2>/dev/null); then
    VERSION=${GIT_TAG#v}
    echo "🔍 Version found from Git tag: $VERSION"
else
    VERSION="0.0.0" # Fallback version
    echo "⚠️ No Git tag found. Using fallback version: $VERSION"
fi

# Set environment variable for linuxdeploy
export LINUXDEPLOY_OUTPUT_VERSION=$VERSION

# --- Build Project ---
echo "🚀 Starting AppImage packaging process..."

# Build the project, passing the version
./build.sh --version "$VERSION"

# --- AppImage Packaging ---

# Download linuxdeploy
echo "📥 Downloading linuxdeploy..."
if [ ! -f "linuxdeploy-x86_64.AppImage" ]; then
    wget -c "https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage"
fi
chmod +x linuxdeploy-x86_64.AppImage

# Clean previous AppDir
echo "🧹 Cleaning previous AppDir..."
rm -rf AppDir

# Create AppDir and copy necessary files
echo "📦 Creating AppDir..."
mkdir -p AppDir/usr/bin
cp "dist/multiscope" AppDir/usr/bin/

# Copy desktop file and icon
cp share/applications/io.github.mallor.MultiScope.desktop AppDir/
cp share/icons/hicolor/scalable/apps/io.github.mallor.MultiScope.svg AppDir/

# Run linuxdeploy to bundle dependencies
echo "🔧 Running linuxdeploy..."
./linuxdeploy-x86_64.AppImage \
    --appdir AppDir \
    --output appimage

# Verify the AppImage
if [ -f MultiScope-*.AppImage ]; then
    echo ""
    echo "✅ AppImage created successfully!"
    echo "📦 File: $(ls MultiScope-*.AppImage)"
    echo "📏 Size: $(du -h MultiScope-*.AppImage | cut -f1)"
else
    echo "❌ AppImage creation failed!"
    exit 1
fi
