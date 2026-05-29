#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

export FLASK_ENV="${FLASK_ENV:-development}"
export LOGIN_REQUIRED="${LOGIN_REQUIRED:-false}"
export PORT="${PORT:-5001}"

if [ ! -x ".venv/bin/python" ]; then
  python3 -m venv .venv
fi

.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
