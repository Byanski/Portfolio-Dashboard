#!/usr/bin/env sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$ROOT_DIR"

find_python() {
  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return 0
  fi
  if command -v python >/dev/null 2>&1; then
    command -v python
    return 0
  fi
  echo "Python 3 is required. Install Python 3 with Tk support, then run ./install.sh again." >&2
  return 1
}

PYTHON_BIN=$(find_python)

echo "Starting Portfolio Builder Installer..."
"$PYTHON_BIN" scripts/installer_gui.py
