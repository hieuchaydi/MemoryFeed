#!/bin/bash
set -euo pipefail

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-7749}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
MEMORYFEED_PUBLIC_MODE="${MEMORYFEED_PUBLIC_MODE:-true}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python not found. Install Python 3.12+ first."
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm not found. Install Node.js 20+ first."
  exit 1
fi

if [ -z "${MEMORYFEED_ADMIN_TOKEN:-}" ]; then
  echo "Missing MEMORYFEED_ADMIN_TOKEN for public mode."
  echo "Set a strong token before running deploy_web.sh"
  exit 1
fi

echo "[1/3] Installing backend dependencies..."
"$PYTHON_BIN" -m pip install -e .

echo "[2/3] Building and serving React+Vite app..."
echo "Host: ${HOST}"
echo "Port: ${PORT}"
echo "Open: http://<your-server-ip>:${PORT}"

MEMORYFEED_PUBLIC_MODE="$MEMORYFEED_PUBLIC_MODE" memoryfeed serve-web --host "${HOST}" --port "${PORT}"
