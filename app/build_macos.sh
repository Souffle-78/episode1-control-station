#!/usr/bin/env bash
# Build a self-contained macOS .app for Episode 1 Arm Control Station.
# Run from anywhere:  ./build_macos.sh
set -euo pipefail

cd "$(dirname "$0")"

PYTHON="${PYTHON:-}"
if [ -z "$PYTHON" ]; then
  if [ -x "/Applications/FreeCAD.app/Contents/Resources/bin/python" ]; then
    PYTHON="/Applications/FreeCAD.app/Contents/Resources/bin/python"
  else
    PYTHON="python3"
  fi
fi

"$PYTHON" - <<'PY'
import PyInstaller, PySide6
print("PyInstaller", PyInstaller.__version__, "PySide6", PySide6.__version__)
PY

rm -rf build/Episode1 dist/Episode1.app dist/Episode1-macOS-*.zip
"$PYTHON" -m PyInstaller \
  --noconfirm --clean --windowed \
  --name Episode1 \
  --icon assets/icon.icns \
  --osx-bundle-identifier com.tsu.episode1 \
  --add-data "../arm/armctl.py:arm" \
  --add-data "../arm/config/joints.json:arm/config" \
  --add-data "../kinematics/__init__.py:kinematics" \
  --add-data "../kinematics/episode1_model.py:kinematics" \
  --add-data "assets:assets" \
  --additional-hooks-dir hooks \
  --collect-all numpy \
  --collect-submodules x42s_stepper \
  --collect-submodules can \
  --collect-submodules serial \
  --collect-submodules episode1_app \
  main.py

# Ad-hoc signature: works on this Mac. For distribution, replace "-" with a
# Developer ID and notarize with notarytool.
codesign --force --deep --sign - dist/Episode1.app

ARCH="$(uname -m)"
ditto -c -k --keepParent "dist/Episode1.app" "dist/Episode1-macOS-${ARCH}.zip"
echo "Built: $(pwd)/dist/Episode1.app"
echo "Zip:   $(pwd)/dist/Episode1-macOS-${ARCH}.zip"
