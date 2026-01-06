#!/bin/bash

set -e # Exit on any error

# Get the directory where the script is located and go to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "🚀 Starting AppImage packaging process..."

# 1. Build the project
./scripts/build.sh

# 2. Download linuxdeploy
echo "📥 Downloading linuxdeploy..."
if [ ! -f "linuxdeploy-x86_64.AppImage" ]; then
    wget -c "https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage"
fi

# 3. Make it executable
chmod +x linuxdeploy-x86_64.AppImage

# 4. Clean previous AppDir
echo "🧹 Cleaning previous AppDir..."
rm -rf AppDir

# 5. Set environment variables
export LINUXDEPLOY_OUTPUT_VERSION="0.9.0"
export NO_STRIP=1  # Disable stripping to avoid errors with modern binaries

# Get GTK paths
GTK_LIBDIR=$(pkg-config --variable=libdir gtk4 2>/dev/null || echo "/usr/lib/x86_64-linux-gnu")
GI_TYPELIB_PATH=$(pkg-config --variable=typelibdir gobject-introspection-1.0 2>/dev/null || echo "/usr/lib/x86_64-linux-gnu/girepository-1.0")

echo "📍 GTK Library Path: $GTK_LIBDIR"
echo "📍 GI Typelib Path: $GI_TYPELIB_PATH"

# 6. Create AppDir structure manually
echo "📦 Creating AppDir structure..."
mkdir -p AppDir/usr/{bin,lib,share/glib-2.0/schemas}
mkdir -p AppDir/usr/lib/girepository-1.0

# 7. Copy the executable
echo "📋 Copying executable..."
cp dist/twinverse AppDir/usr/bin/

# 8. Copy GTK and GObject Introspection libraries
echo "📚 Copying GTK libraries..."

# Function to copy library and its dependencies
copy_lib_and_deps() {
    local lib=$1
    local search_paths=("$GTK_LIBDIR" "/usr/lib/x86_64-linux-gnu" "/usr/lib")

    for path in "${search_paths[@]}"; do
        if [ -f "$path/$lib" ]; then
            echo "  ✓ Copying $lib"
            cp -L "$path/$lib" AppDir/usr/lib/ 2>/dev/null || true

            # Copy symlinks
            local base_name=$(echo $lib | sed 's/\.so.*//')
            find "$path" -name "${base_name}.so*" -exec cp -L {} AppDir/usr/lib/ 2>/dev/null \; || true
            return 0
        fi
    done
    return 1
}

# Critical GTK4 and dependencies
REQUIRED_LIBS=(
    "libgtk-4.so.1"
    "libadwaita-1.so.0"
    "libgdk_pixbuf-2.0.so.0"
    "libgio-2.0.so.0"
    "libglib-2.0.so.0"
    "libgobject-2.0.so.0"
    "libgmodule-2.0.so.0"
    "libpango-1.0.so.0"
    "libpangocairo-1.0.so.0"
    "libpangoft2-1.0.so.0"
    "libcairo.so.2"
    "libcairo-gobject.so.2"
    "libharfbuzz.so.0"
    "libgraphene-1.0.so.0"
    "libepoxy.so.0"
    "libfontconfig.so.1"
    "libfreetype.so.6"
    "libfribidi.so.0"
    "libpixman-1.so.0"
    "libpng16.so.16"
    "libjpeg.so.8"
    "libtiff.so.6"
    "libxml2.so.2"
    "libxkbcommon.so.0"
    "libwayland-client.so.0"
    "libwayland-cursor.so.0"
    "libwayland-egl.so.1"
    "libX11.so.6"
    "libXext.so.6"
    "libXrender.so.1"
    "libXi.so.6"
    "libXfixes.so.3"
    "libXcursor.so.1"
    "libXdamage.so.1"
    "libXrandr.so.2"
    "libXinerama.so.1"
    "libEGL.so.1"
    "libGLX.so.0"
    "libGL.so.1"
    "libGLdispatch.so.0"
    "libdrm.so.2"
    "libgbm.so.1"
    "libxcb.so.1"
    "libxcb-dri2.so.0"
    "libxcb-dri3.so.0"
    "libxcb-present.so.0"
    "libxcb-sync.so.1"
    "libxcb-xfixes.so.0"
    "libxshmfence.so.1"
    "libX11-xcb.so.1"
)

for lib in "${REQUIRED_LIBS[@]}"; do
    copy_lib_and_deps "$lib"
done

# 9. Copy GObject Introspection typelibs
echo "📚 Copying GI typelibs..."
REQUIRED_TYPELIBS=(
    "Gtk-4.0.typelib"
    "Gsk-4.0.typelib"
    "Graphene-1.0.typelib"
    "Adw-1.typelib"
    "Gdk-4.0.typelib"
    "GLib-2.0.typelib"
    "GObject-2.0.typelib"
    "Gio-2.0.typelib"
    "GioUnix-2.0.typelib"
    "GdkPixbuf-2.0.typelib"
    "Pango-1.0.typelib"
    "PangoCairo-1.0.typelib"
    "PangoFT2-1.0.typelib"
    "cairo-1.0.typelib"
    "HarfBuzz-0.0.typelib"
    "freetype2-2.0.typelib"
    "GModule-2.0.typelib"
    "xlib-2.0.typelib"
)

for typelib in "${REQUIRED_TYPELIBS[@]}"; do
    if [ -f "$GI_TYPELIB_PATH/$typelib" ]; then
        echo "  ✓ Copying $typelib"
        cp "$GI_TYPELIB_PATH/$typelib" AppDir/usr/lib/girepository-1.0/
    else
        echo "  ✗ Not found: $typelib"
    fi
done

# 10. Copy GLib schemas
echo "📚 Copying GLib schemas..."
SCHEMA_DIR="/usr/share/glib-2.0/schemas"
if [ -d "$SCHEMA_DIR" ]; then
    cp -r "$SCHEMA_DIR"/* AppDir/usr/share/glib-2.0/schemas/ 2>/dev/null || true
    # Compile schemas
    if command -v glib-compile-schemas &> /dev/null; then
        glib-compile-schemas AppDir/usr/share/glib-2.0/schemas/
        echo "  ✓ Schemas compiled"
    fi
fi

# 11. Copy icon themes (important for GTK)
echo "📚 Copying icon themes..."
mkdir -p AppDir/usr/share/icons
if [ -d "/usr/share/icons/Adwaita" ]; then
    cp -r /usr/share/icons/Adwaita AppDir/usr/share/icons/ 2>/dev/null || true
    echo "  ✓ Adwaita icons copied"
fi

if [ -d "/usr/share/icons/hicolor" ]; then
    cp -r /usr/share/icons/hicolor AppDir/usr/share/icons/ 2>/dev/null || true
    echo "  ✓ Hicolor icons copied"
fi

# 12. Create AppRun script
echo "📝 Creating AppRun script..."
cat > AppDir/AppRun << 'APPRUN_EOF'
#!/bin/bash
SELF=$(readlink -f "$0")
HERE=${SELF%/*}

# Set up environment for GTK
export PATH="${HERE}/usr/bin:${PATH}"
export LD_LIBRARY_PATH="${HERE}/usr/lib:${LD_LIBRARY_PATH}"
export GI_TYPELIB_PATH="${HERE}/usr/lib/girepository-1.0:${GI_TYPELIB_PATH}"
export XDG_DATA_DIRS="${HERE}/usr/share:${XDG_DATA_DIRS:-/usr/local/share:/usr/share}"
export GSETTINGS_SCHEMA_DIR="${HERE}/usr/share/glib-2.0/schemas:${GSETTINGS_SCHEMA_DIR}"

# GTK4 specific
export GTK_PATH="${HERE}/usr/lib/gtk-4.0"
export GTK_EXE_PREFIX="${HERE}/usr"
export GTK_DATA_PREFIX="${HERE}/usr"

# Disable GTK's schemas cache (use our bundled schemas)
export GSETTINGS_BACKEND=memory

# Run the application
exec "${HERE}/usr/bin/twinverse" "$@"
APPRUN_EOF

chmod +x AppDir/AppRun

# 13. Copy desktop file and icon
echo "📋 Copying desktop file and icon..."
mkdir -p AppDir/usr/share/applications
mkdir -p AppDir/usr/share/icons/hicolor/scalable/apps
mkdir -p AppDir/usr/share/metainfo
cp share/applications/io.github.mall0r.Twinverse.desktop AppDir/usr/share/applications/
cp share/icons/hicolor/scalable/apps/io.github.mall0r.Twinverse.svg AppDir/usr/share/icons/hicolor/scalable/apps/
cp share/icons/hicolor/scalable/apps/io.github.mall0r.Twinverse.svg AppDir/io.github.mall0r.Twinverse.svg
cp share/applications/io.github.mall0r.Twinverse.desktop AppDir/io.github.mall0r.Twinverse.desktop
cp share/metainfo/io.github.mall0r.Twinverse.metainfo.xml AppDir/usr/share/metainfo/

# 14. Run linuxdeploy to finalize (without strip) and create AppImage
echo "🔧 Running linuxdeploy..."
NO_STRIP=1 ./linuxdeploy-x86_64.AppImage \
    --appdir AppDir \
    --output appimage

# 15. Verify the AppImage
if [ -f Twinverse-*.AppImage ]; then
    echo ""
    echo "✅ AppImage created successfully!"
    echo "📦 File: $(ls Twinverse-*.AppImage)"
    echo "📏 Size: $(du -h Twinverse-*.AppImage | cut -f1)"
    echo ""
    echo "🎉 This AppImage is fully self-contained and should work on any Linux system!"
    echo ""
    echo "📝 Testing instructions:"
    echo "  1. Transfer to Debian: scp Twinverse-*.AppImage user@debian:/path/"
    echo "  2. Make executable: chmod +x Twinverse-*.AppImage"
    echo "  3. Run directly: ./Twinverse-*.AppImage"
    echo "  4. Or extract: ./Twinverse-*.AppImage --appimage-extract && cd squashfs-root && ./AppRun"
    echo ""
else
    echo "❌ AppImage creation failed!"
    exit 1
fi
