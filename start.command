#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
# Reuse the task's tested environment here, or create a project-local one elsewhere.
if [ -x ../../work/prototype-venv/bin/python ]; then
  EWB_PYTHON=../../work/prototype-venv/bin/python
else
  EWB_PYTHON="${EWB_PYTHON:-python3}"
  "$EWB_PYTHON" -c 'import sys; assert sys.version_info >= (3,11), "Python 3.11 or newer is required"'
  if [ ! -x .venv/bin/python ]; then
    echo 'Provision .venv and dependencies first; startup never downloads packages. See README offline setup.' >&2
    exit 1
  fi
  EWB_PYTHON=.venv/bin/python
fi
if [ -z "${EWB_WORKER_IMAGE:-}" ] && [ -f data/worker-image.txt ]; then
  export EWB_WORKER_IMAGE="$(cat data/worker-image.txt)"
fi
if [ -f data/local-model.json ]; then
  if [ -z "${EWB_LOCAL_MODEL_URL:-}" ]; then
    export EWB_LOCAL_MODEL_URL="$("$EWB_PYTHON" -c 'import json; print(json.load(open("data/local-model.json"))["url"])')"
  fi
  if [ -z "${EWB_LOCAL_MODEL:-}" ]; then
    export EWB_LOCAL_MODEL="$("$EWB_PYTHON" -c 'import json; print(json.load(open("data/local-model.json"))["model"])')"
  fi
fi
"$EWB_PYTHON" scripts/setup.py
printf '\nOpen http://127.0.0.1:8765 in your browser. Press Ctrl+C to stop.\n\n'
exec "$EWB_PYTHON" -m uvicorn backend.app:app --host 127.0.0.1 --port 8765
