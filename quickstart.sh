#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "[1/4] Running setup..."
bash ./setup.sh

echo "[2/4] Starting backend on :7749 ..."
memoryfeed serve > /tmp/memoryfeed-backend.log 2>&1 &
BACK_PID=$!

echo "[3/4] Starting frontend on :5173 ..."
(
  cd frontend
  npm run dev -- --host 127.0.0.1 --port 5173 > /tmp/memoryfeed-frontend.log 2>&1
) &
FRONT_PID=$!

cleanup() {
  echo ""
  echo "Stopping MemoryFeed..."
  kill "$BACK_PID" >/dev/null 2>&1 || true
  kill "$FRONT_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

sleep 3
python3 - <<'PY'
import webbrowser
webbrowser.open("http://localhost:5173")
print("Opened: http://localhost:5173")
PY

echo ""
echo "MemoryFeed is running."
echo "- Frontend: http://localhost:5173"
echo "- Backend : http://localhost:7749"
echo "- Logs    : /tmp/memoryfeed-backend.log and /tmp/memoryfeed-frontend.log"
echo "Press Ctrl+C to stop."

wait
