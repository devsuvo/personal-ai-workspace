#!/usr/bin/env bash
set -euo pipefail

# Build Personal AI Workspace macOS .app bundle and .dmg installer
# Run on macOS (Apple Silicon arm64 or Intel x86_64)

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP_NAME="PersonalAIWorkspace"
VERSION="1.0.0"
DIST_DIR="${ROOT_DIR}/dist/macos"

echo "=== [1/5] Building frontend production bundle ==="
(cd "${ROOT_DIR}/frontend" && npm install && npm run build)

echo "=== [2/5] Preparing Python venv and icons ==="
if [ ! -d "${ROOT_DIR}/backend/.venv" ]; then
  python3 -m venv "${ROOT_DIR}/backend/.venv"
fi
source "${ROOT_DIR}/backend/.venv/bin/activate"
pip install --upgrade pip
pip install -r "${ROOT_DIR}/backend/requirements.txt" pyinstaller==6.13.0

python "${ROOT_DIR}/packaging/generate_icons.py"

ICONSET="${ROOT_DIR}/packaging/icons/app_icon.iconset"
rm -rf "${ICONSET}"
mkdir -p "${ICONSET}"
for size in 16 32 128 256 512; do
  sips -z "${size}" "${size}" "${ROOT_DIR}/packaging/icons/app_icon.png" --out "${ICONSET}/icon_${size}x${size}.png" >/dev/null
  sips -z "$((size * 2))" "$((size * 2))" "${ROOT_DIR}/packaging/icons/app_icon.png" --out "${ICONSET}/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil -c icns "${ICONSET}" -o "${ROOT_DIR}/packaging/icons/app_icon.icns"

echo "=== [3/5] Bundling macOS .app with PyInstaller ==="
mkdir -p "${DIST_DIR}"
pyinstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name "${APP_NAME}" \
  --icon "${ROOT_DIR}/packaging/icons/app_icon.icns" \
  --distpath "${DIST_DIR}" \
  --workpath "${ROOT_DIR}/build/macos" \
  --paths "${ROOT_DIR}/backend" \
  --add-data "${ROOT_DIR}/frontend/dist:frontend_dist" \
  --add-data "${ROOT_DIR}/backend/alembic:alembic" \
  --add-data "${ROOT_DIR}/backend/alembic.ini:." \
  --hidden-import "keyring.backends.macOS" \
  "${ROOT_DIR}/backend/desktop_launcher.py"

echo "=== [4/5] Creating DMG installer ==="
DMG_PATH="${DIST_DIR}/${APP_NAME}-${VERSION}-$(uname -m).dmg"
rm -f "${DMG_PATH}"
hdiutil create \
  -volname "Personal AI Workspace" \
  -srcfolder "${DIST_DIR}/${APP_NAME}.app" \
  -ov \
  -format UDZO \
  "${DMG_PATH}"

echo "=== [5/5] Complete ==="
echo "App bundle: ${DIST_DIR}/${APP_NAME}.app"
echo "DMG image:  ${DMG_PATH}"
