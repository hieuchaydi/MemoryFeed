#!/bin/bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"
if [ -f .env ]; then
  # shellcheck disable=SC2046
  export $(grep -v '^#' .env | xargs)
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python not found. Please install Python 3.12+ first."
  exit 1
fi

PY_VER=$($PYTHON_BIN -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 12 ]; }; then
  echo "Python 3.12+ is required. Found: $PY_VER"
  exit 1
fi

echo "Python version OK: $PY_VER"

OFFLINE_ONLY_VALUE="${OFFLINE_ONLY:-0}"
AI_PROVIDER="$(printf '%s' "${MEMORYFEED_AI_PROVIDER:-auto}" | tr '[:upper:]' '[:lower:]')"

is_truthy() {
  case "${1,,}" in
    1|true|yes|on) return 0 ;;
    *) return 1 ;;
  esac
}

if is_truthy "$OFFLINE_ONLY_VALUE"; then
  AI_PROVIDER="none"
fi

if [ "$AI_PROVIDER" = "gemini" ] && [ -z "${GEMINI_API_KEY:-}" ]; then
  echo "Missing GEMINI_API_KEY (required by MEMORYFEED_AI_PROVIDER=gemini)"
  exit 1
fi

if [ "$AI_PROVIDER" = "groq" ] && [ -z "${GROQ_API_KEY:-}" ]; then
  echo "Missing GROQ_API_KEY (required by MEMORYFEED_AI_PROVIDER=groq)"
  exit 1
fi

echo "Installing MemoryFeed in editable mode..."
$PYTHON_BIN -m pip install -e .

if command -v npm >/dev/null 2>&1; then
  echo "Installing frontend dependencies..."
  (cd frontend && npm install)
else
  echo "npm not found. Frontend build commands will be unavailable."
fi

echo ""
echo "AI mode: OFFLINE_ONLY=${OFFLINE_ONLY_VALUE} MEMORYFEED_AI_PROVIDER=${AI_PROVIDER}"
if [ -n "${GEMINI_API_KEY:-}" ]; then
  echo "- Gemini API key: set"
else
  echo "- Gemini API key: not set"
fi
if [ -n "${GROQ_API_KEY:-}" ]; then
  echo "- Groq API key  : set"
else
  echo "- Groq API key  : not set"
fi
echo ""
echo "Extension (Chrome/Edge/Brave): load unpacked from ./extension/chrome/"
echo "Extension (Firefox): load manifest ./extension/firefox/manifest.json"
echo "Run: memoryfeed models"
echo "Run: memoryfeed serve"
echo "Run MCP (stdio): memoryfeed mcp --transport stdio"
echo "One-command run (Linux/macOS): bash quickstart.sh"
echo "One-command run (Windows): .\\quickstart.ps1"
echo "Public deploy (Linux/macOS): bash deploy_web.sh"
echo "Public deploy (Windows): .\\deploy_web.ps1"
echo "Optional C++ accel: memoryfeed build-native"
echo "Optional frontend build: memoryfeed build-frontend"

$PYTHON_BIN - <<'PY'
import webbrowser
webbrowser.open("http://localhost:7749")
print("Attempted to open browser at http://localhost:7749")
PY
