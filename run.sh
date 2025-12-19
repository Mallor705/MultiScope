#!/bin/bash

cd "$(dirname "$0")"

# Compile GResource bundle
(cd src/gui/resources && glib-compile-resources --target=compiled.gresource resources.xml)

# Force a clean venv
if [ -d ".venv" ]; then
    rm -rf .venv
fi

python3 -m venv .venv

source .venv/bin/activate

pip install -r requirements.txt

python3 multiscope.py "$@"
