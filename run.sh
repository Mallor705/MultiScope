#!/bin/bash

cd "$(dirname "$0")"

# Compile GResource
echo "📦 Compiling GResource..."
glib-compile-resources \
  --target=src/gui/resources/compiled.gresource \
  --sourcedir=src/gui/resources \
  src/gui/resources/resources.xml

# Create venv if it doesn't exist
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

# Run application
echo "🚀 Running application..."
python3 multiscope.py "$@"
