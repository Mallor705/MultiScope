#!/bin/bash

set -e

./package-flatpak.sh

APP_ID="io.github.mallor.MultiScope"
REPO_DIR="flatpak-repo"
BUNDLE_NAME="MultiScope.flatpak"

echo "Uninstalling..."
echo ""
flatpak uninstall $APP_ID
echo ""
echo "Installing..."
echo ""
flatpak install --user $BUNDLE_NAME
echo ""
echo "Running..."
echo ""
flatpak run $APP_ID
