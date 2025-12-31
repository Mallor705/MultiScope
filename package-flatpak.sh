#!/bin/bash

# MultiScope Flatpak Build Script
set -e

# Compile GResource
echo "📦 Compiling GResource..."
glib-compile-resources \
  --target=src/gui/resources/compiled.gresource \
  --sourcedir=src/gui/resources \
  src/gui/resources/resources.xml

echo "🚀 Starting MultiScope Flatpak build..."

# Check if flatpak-builder is installed
if ! command -v flatpak-builder &> /dev/null; then
    echo "❌ flatpak-builder is not installed!"
    echo "Install it with: sudo apt install flatpak-builder (Debian/Ubuntu)"
    echo "                 sudo dnf install flatpak-builder (Fedora)"
    echo "                 sudo pacman -S flatpak-builder (Arch Linux)"
    exit 1
fi

# Check if required runtimes are installed
echo "🔍 Checking for required Flatpak runtimes..."
if ! flatpak list --runtime | grep -q "org.gnome.Platform.*49"; then
    echo "📦 Installing GNOME Platform runtime..."
    flatpak install -y flathub org.gnome.Platform//49 org.gnome.Sdk//49
fi

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build-dir .flatpak-builder

# Build the Flatpak
echo "🔨 Building Flatpak..."
flatpak-builder --force-clean --install-deps-from=flathub \
    build-dir io.github.mallor.MultiScope.yaml

# Test the build
echo "✅ Build complete! Testing..."
flatpak-builder --run build-dir io.github.mallor.MultiScope.yaml multiscope --help

echo ""
echo "🎉 Flatpak build successful!"
echo ""


# MultiScope Flatpak Packaging Script
echo "📦 Starting MultiScope Flatpak packaging..."

APP_ID="io.github.mallor.MultiScope"
REPO_DIR="flatpak-repo"
BUNDLE_NAME="MultiScope.flatpak"

# Create repository if it doesn't exist
if [ ! -d "$REPO_DIR" ]; then
    echo "📁 Creating flatpak repository..."
    ostree init --mode=archive-z2 --repo="$REPO_DIR"
fi

# Export to repository
echo "📤 Exporting to repository..."
flatpak-builder --force-clean --repo="$REPO_DIR" build-dir "$APP_ID.yaml"

# Create single-file bundle
echo "📦 Creating flatpak bundle..."
flatpak build-bundle "$REPO_DIR" "$BUNDLE_NAME" "$APP_ID"

# Get bundle size
BUNDLE_SIZE=$(du -h "$BUNDLE_NAME" | cut -f1)

echo ""
echo "✅ Flatpak package created successfully!"
echo "📦 File: $BUNDLE_NAME"
echo "📏 Size: $BUNDLE_SIZE"
echo ""
echo "🚀 Distribution instructions:"
echo ""
echo "To install on any system:"
echo "  flatpak install $BUNDLE_NAME"
echo ""
echo "To install without system prompts:"
echo "  flatpak install --user $BUNDLE_NAME"
echo ""
echo "To run after installation:"
echo "  flatpak run $APP_ID"
echo ""
echo "To uninstall:"
echo "  flatpak uninstall $APP_ID"
echo ""
echo "📤 To publish to Flathub:"
echo "  1. Fork https://github.com/flathub/flathub"
echo "  2. Add your manifest: $APP_ID.yaml"
echo "  3. Submit pull request"
echo ""
