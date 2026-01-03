#!/bin/bash

# MultiScope Flatpak Build Script
set -e

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

# Get current date
CURRENT_DATE=$(date +%Y-%m-%d)

# --- Build Environment Setup ---
BUILD_DIR="build/flatpak"
APP_ID="io.github.mallor.MultiScope"
MANIFEST_SRC="io.github.mallor.MultiScope.yaml"
MANIFEST_DEST="$BUILD_DIR/$MANIFEST_SRC"
METAINFO_SRC="share/metainfo/$APP_ID.metainfo.xml.in"
METAINFO_DEST="$BUILD_DIR/share/metainfo/$APP_ID.metainfo.xml"

echo "🔧 Setting up build environment in: $BUILD_DIR"

# Clean and create build directory
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/share/metainfo"

# --- Pre-build Steps ---

# Process metainfo template
echo "📝 Processing metainfo template..."
sed -e "s/@@VERSION@@/$VERSION/g" \
    -e "s/@@DATE@@/$CURRENT_DATE/g" \
    "$METAINFO_SRC" > "$METAINFO_DEST"

# Copy manifest and python modules to build directory
cp "$MANIFEST_SRC" "$MANIFEST_DEST"
cp -r "flatpak" "$BUILD_DIR/"

# Replace the original metainfo path with the generated one in the manifest
echo "✏️ Updating manifest to use generated metainfo file..."
sed -i "s|share/metainfo/io.github.mallor.MultiScope.metainfo.xml|$METAINFO_DEST|g" "$MANIFEST_DEST"

# Compile GResource
echo "📦 Compiling GResource..."
glib-compile-resources \
  --target=res/compiled.gresource \
  --sourcedir=res \
  res/resources.xml

# --- Flatpak Build ---
echo "🚀 Starting MultiScope Flatpak build..."

# Check for flatpak-builder
if ! command -v flatpak-builder &> /dev/null; then
    echo "❌ flatpak-builder is not installed!"
    exit 1
fi

# Install required runtimes
if ! flatpak list --runtime | grep -q "org.gnome.Platform.*49"; then
    echo "📦 Installing GNOME Platform runtime..."
    flatpak install --user -y flathub org.gnome.Platform//49 org.gnome.Sdk//49
fi

# Clean previous builds
rm -rf flatpak-build-dir .flatpak-builder

# Build the Flatpak
echo "🔨 Building Flatpak..."
flatpak-builder --user --force-clean --install-deps-from=flathub \
    flatpak-build-dir "$MANIFEST_DEST"

# Test the build
echo "✅ Build complete! Testing..."
flatpak-builder --user --run flatpak-build-dir "$MANIFEST_DEST" multiscope --help

# --- Flatpak Packaging ---
echo "📦 Starting MultiScope Flatpak packaging..."

REPO_DIR="flatpak-repo"
BUNDLE_NAME="MultiScope-v$VERSION.flatpak"

# Create repository
ostree init --mode=archive-z2 --repo="$REPO_DIR"

# Export to repository
flatpak-builder --force-clean --repo="$REPO_DIR" flatpak-build-dir "$MANIFEST_DEST"

# Create single-file bundle
echo "📦 Creating flatpak bundle: $BUNDLE_NAME"
flatpak build-bundle "$REPO_DIR" "$BUNDLE_NAME" "$APP_ID"

echo ""
echo "🎉 Flatpak package created successfully!"
echo "📦 File: $BUNDLE_NAME"
echo "📏 Size: $(du -h "$BUNDLE_NAME" | cut -f1)"
echo ""
