#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v python3 &>/dev/null; then
  echo "Error: python3 not found. Install it via: brew install python3" >&2
  exit 1
fi

if [ ! -d "$SCRIPT_DIR/.venv" ]; then
  echo "Setting up Python environment..." >&2
  python3 -m venv "$SCRIPT_DIR/.venv"
  "$SCRIPT_DIR/.venv/bin/pip" install -q -r "$SCRIPT_DIR/requirements.txt"
fi

exec "$SCRIPT_DIR/.venv/bin/python3" "$SCRIPT_DIR/scripts/search_flights.py" "$@"
