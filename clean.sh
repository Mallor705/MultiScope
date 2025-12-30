#!/bin/bash
set -e

echo "═══════════════════════════════════════════════════════════"
echo "  🧹 Cleaning up..."
echo "═══════════════════════════════════════════════════════════"
echo ""

# Passo 1: Stop processes
echo "1️⃣  Stoping processes..."
pkill -9 -f multiscope 2>/dev/null || true
pkill -9 -f gamescope 2>/dev/null || true
pkill -9 -f wine 2>/dev/null || true
sleep 1
echo "   ✅ Processes stopped"

# Passo 2: Cleaning cache
echo "2️⃣  Cleaning cache..."
find . -type d -name "__pycache__" -exec rm -rf {} \;
sleep 1
echo "   ✅ Cache cleaned"

# Passo 3: Cleaning files build
echo "3️⃣  Cleaning files build..."
rm -rf build dist AppDir .venv squashfs-root .flatpak-builder build-dir flatpak-repo
rm -rf *.spec
rm -rf *.AppImage
rm -rf *.log
rm -rf *.flatpak
sleep 1
echo "   ✅ Files cleaned"

# Passo 4: Finalizing
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  ✅ CLEANED!"
echo "═══════════════════════════════════════════════════════════"
