#!/bin/bash

set -e # Exit on any error

echo "🚀 Starting AppImage packaging process..."

# 1. Build the project
./build.sh

# 2. Download linuxdeploy
wget -c "https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage" -O linuxdeploy-x86_64.AppImage

# 3. Make linuxdeploy executable
chmod +x linuxdeploy-x86_64.AppImage

# 4. Run linuxdeploy

export LINUXDEPLOY_OUTPUT_VERSION="0.8.0"

./linuxdeploy-x86_64.AppImage \
    --appdir AppDir \
    --executable dist/multiscope \
    --icon-file res/multiscope.svg \
    --desktop-file res/multiscope.desktop \
    --output appimage

echo "✅ AppImage created successfully!"
