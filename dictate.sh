#!/usr/bin/env bash
# Launch the dictation engine using the project's virtualenv.
set -euo pipefail
cd "$(dirname "$0")"

if [[ ! -d .venv ]]; then
  echo "Setting up virtualenv (first run)…"
  python3 -m venv .venv
  .venv/bin/python -m pip install --upgrade pip wheel >/dev/null
  .venv/bin/python -m pip install -r requirements.txt
fi

exec .venv/bin/python -m dictate "$@"
