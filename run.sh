#!/bin/bash

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    python3.12 -m venv .venv
fi

source .venv/bin/activate

pip install -r requirements.txt

python3.12 linuxcoop.py "$@"