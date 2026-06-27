#!/usr/bin/env bash
#
# Build a distributable .dmg from the PyInstaller-built "Voca.app".
#
# Usage:
#   desktop/macos/dmg.sh [arch]
#
#   arch  optional: "arm64" or "x64". If omitted it is detected from the host
#         (`uname -m`: arm64 -> arm64, x86_64 -> x64).
#
# Expects the app at:   dist/Voca.app   (relative to repo root)
# Produces:             dist/Voca-<version>-mac-<arch>.dmg
#
# Uses `create-dmg` if installed (prettier, drag-to-Applications layout),
# otherwise falls back to plain `hdiutil`.
set -euo pipefail

# Resolve repo root from this script's location (desktop/macos/ -> repo root).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${REPO_ROOT}"

APP_NAME="Voca"
APP_PATH="dist/${APP_NAME}.app"

# --- arch -------------------------------------------------------------------
ARCH="${1:-}"
if [[ -z "${ARCH}" ]]; then
  case "$(uname -m)" in
    arm64)  ARCH="arm64" ;;
    x86_64) ARCH="x64" ;;
    *)      ARCH="$(uname -m)" ;;
  esac
fi

# --- version (read from dictate/__init__.py) --------------------------------
VERSION="$(sed -n 's/^__version__[[:space:]]*=[[:space:]]*["'\'']\([^"'\'']*\)["'\''].*/\1/p' dictate/__init__.py)"
VERSION="${VERSION:-0.0.0}"

DMG_NAME="Voca-${VERSION}-mac-${ARCH}.dmg"
DMG_PATH="dist/${DMG_NAME}"

if [[ ! -d "${APP_PATH}" ]]; then
  echo "ERROR: ${APP_PATH} not found. Build it first with PyInstaller:" >&2
  echo "  pyinstaller --noconfirm --clean desktop/pyinstaller/Voca.spec" >&2
  exit 1
fi

rm -f "${DMG_PATH}"
echo "Building ${DMG_NAME} from ${APP_PATH} (arch=${ARCH}, version=${VERSION})"

if command -v create-dmg >/dev/null 2>&1; then
  echo "Using create-dmg"
  # create-dmg returns 2 when it succeeds but cannot codesign the dmg itself;
  # treat that as success.
  create-dmg \
    --volname "${APP_NAME}" \
    --window-pos 200 120 \
    --window-size 660 400 \
    --icon-size 120 \
    --icon "${APP_NAME}.app" 165 175 \
    --hide-extension "${APP_NAME}.app" \
    --app-drop-link 495 175 \
    --no-internet-enable \
    "${DMG_PATH}" \
    "${APP_PATH}" \
    || [[ $? -eq 2 ]]
else
  echo "create-dmg not found — falling back to hdiutil"
  STAGE="$(mktemp -d)"
  cp -R "${APP_PATH}" "${STAGE}/"
  ln -s /Applications "${STAGE}/Applications"
  hdiutil create \
    -volname "${APP_NAME}" \
    -srcfolder "${STAGE}" \
    -ov \
    -format UDZO \
    "${DMG_PATH}"
  rm -rf "${STAGE}"
fi

echo "Created ${DMG_PATH}"
