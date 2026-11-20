#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"
if [[ -x /Applications/FreeCAD.app/Contents/Resources/bin/python ]]; then
  PY=/Applications/FreeCAD.app/Contents/Resources/bin/python
fi
exec "$PY" main.py "$@"
