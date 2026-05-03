#!/bin/bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"

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

if ! curl -sSf http://localhost:11434/api/tags >/dev/null 2>&1; then
  echo "Ollama is not running on localhost:11434"
  echo "Install: https://ollama.com/download"
  echo "Then run: ollama serve"
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

ensure_model() {
  local model_name="$1"
  if curl -s http://localhost:11434/api/tags | grep -q "\"name\"[[:space:]]*:[[:space:]]*\"${model_name}\""; then
    echo "Model exists: ${model_name}"
  else
    echo "Pulling model: ${model_name}"
    ollama pull "${model_name}"
  fi
}

ensure_model "qwen2.5:7b"
ensure_model "llava:7b"

echo ""
echo "Extension (Chrome/Edge/Brave): load unpacked from ./extension/chrome/"
echo "Extension (Firefox): load manifest ./extension/firefox/manifest.json"
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
