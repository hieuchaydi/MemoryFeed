# MemoryFeed

![MemoryFeed Logo](frontend/public/logo-memoryfeed.svg)

MemoryFeed is a local-first social memory system:

- Browser extension captures social posts after 3s dwell.
- FastAPI backend stores content in SQLite (WAL) + FTS5.
- LanceDB stores semantic vectors for multilingual search.
- Optional vision pipeline (Gemini) captions images/memes asynchronously.
- Optional text rewrite/summarization uses Groq with Qwen.
- React + Vite + TypeScript frontend is the main operator console.
- Optional C++ native acceleration speeds critical ranking/text ops.
- Item metadata management (star/note/tags), export/import, and queue observability.
- Active Feed ranks memories by personal heat, decay, resurfacing gap, and current context.

Local-first by default. Captured data is stored locally. Optional cloud AI providers may process selected text/images only when explicitly configured.

## Privacy Modes

### 1. Offline / Local-only mode
- `OFFLINE_ONLY=1`
- `MEMORYFEED_AI_PROVIDER=none`
- No Gemini/Groq calls are made.
- No cloud API keys are required.
- Capture, storage, FTS search, timeline, feed, export/import all stay local.

### 2. Hybrid AI mode
- `OFFLINE_ONLY=0`
- `MEMORYFEED_AI_PROVIDER=auto|gemini|groq`
- Enable only the providers you want.
- API keys are required only for enabled providers.

### 3. Data that may be sent to cloud providers in hybrid mode
- Gemini: selected image bytes + caption prompt.
- Groq: selected text/caption snippets for rewrite/summarization.
- Core storage data stays local unless you explicitly export/share it.

### 4. How to disable all cloud AI
```bash
OFFLINE_ONLY=1
MEMORYFEED_AI_PROVIDER=none
```

## Architecture

- `extension/chrome`: Chromium extension (Chrome/Edge/Brave).
- `extension/firefox`: Firefox extension package.
- `backend`: capture normalization, store, indexing, search, server.
- `frontend`: React app (Search / Active Feed / Timeline / Stats).
- `native`: pybind11 C++ module (`memoryfeed_native`) for acceleration.

## Requirements

- Python 3.12+
- Node.js 20+

Optional keys (hybrid mode only):
- `GEMINI_API_KEY`
- `GROQ_API_KEY`

Optional for C++ acceleration:
- Windows: Visual Studio C++ Build Tools
- Linux/macOS: GCC/Clang with C++17

## Setup Modes

### A. Offline basic mode (recommended for strict privacy)

Linux/macOS:
```bash
export OFFLINE_ONLY=1
export MEMORYFEED_AI_PROVIDER=none
bash quickstart.sh
```

Windows PowerShell:
```powershell
$env:OFFLINE_ONLY = "1"
$env:MEMORYFEED_AI_PROVIDER = "none"
.\quickstart.ps1
```

### B. Hybrid AI mode (Gemini/Groq opt-in)

Linux/macOS:
```bash
export OFFLINE_ONLY=0
export MEMORYFEED_AI_PROVIDER=auto
export GEMINI_API_KEY="..."
export GROQ_API_KEY="..."
bash quickstart.sh
```

Windows PowerShell:
```powershell
$env:OFFLINE_ONLY = "0"
$env:MEMORYFEED_AI_PROVIDER = "auto"
$env:GEMINI_API_KEY = "..."
$env:GROQ_API_KEY = "..."
.\quickstart.ps1
```

### C. Public web mode

Warning: this serves personal memory data over the network. Use only on trusted networks.

Required:
- `MEMORYFEED_PUBLIC_MODE=true`
- `MEMORYFEED_ADMIN_TOKEN=<strong-random-token>`

Linux/macOS:
```bash
export MEMORYFEED_PUBLIC_MODE=true
export MEMORYFEED_ADMIN_TOKEN="replace-with-long-random-token"
bash deploy_web.sh
```

Windows PowerShell:
```powershell
$env:MEMORYFEED_PUBLIC_MODE = "true"
$env:MEMORYFEED_ADMIN_TOKEN = "replace-with-long-random-token"
.\deploy_web.ps1
```

Optional custom host/port:
```bash
HOST=0.0.0.0 PORT=8080 bash deploy_web.sh
```

```powershell
.\deploy_web.ps1 -HostIp 0.0.0.0 -Port 8080
```

### D. MCP mode

Warning: MCP can expose memory excerpts to connected agent clients.

Default safety controls:
- `MEMORYFEED_MCP_MAX_RESULTS=5`
- `MEMORYFEED_MCP_ALLOW_TIMELINE=false`
- `MEMORYFEED_MCP_ALLOW_ACTIVE_FEED=true`
- `MEMORYFEED_MCP_REDACT_OUTPUT=true`

Run MCP over stdio:
```bash
memoryfeed mcp --transport stdio
```

Run MCP over streamable HTTP:
```bash
memoryfeed mcp --transport streamable-http --host 127.0.0.1 --port 7748 --path /mcp
```

## Manual Setup

Linux/macOS:
```bash
bash setup.sh
memoryfeed serve
cd frontend && npm run dev
```

Windows PowerShell:
```powershell
bash setup.sh
memoryfeed serve
cd frontend; npm run dev
```

Frontend dev URL: `http://localhost:5173`  
Backend API URL: `http://localhost:7749`

## Security Controls

- Admin endpoints (`/api/admin/export`, `/api/admin/import`, `/api/admin/reset`) support Bearer token auth via `MEMORYFEED_ADMIN_TOKEN`.
- Public bind protection: CLI refuses `0.0.0.0` unless `MEMORYFEED_PUBLIC_MODE=true` and admin token is set.
- MCP defaults to bounded results + optional output redaction and logs each tool call (`timestamp`, `tool_name`, `query`, `result_count`).
- Extension host permissions use explicit domains only (no `https://*/*`).

See [SECURITY.md](SECURITY.md) for threat model and mitigations.

## API Endpoints

- `POST /capture` and `POST /api/capture`
- `GET /api/search`
- `GET /api/feed?limit=&mode=default|focus|light|explore`
- `POST /api/resurface`
- `POST /api/feed/surfaced`
- `POST /api/feed/archive`
- `GET /api/timeline`
- `GET /api/stats`
- `GET /api/native/status`
- `GET /api/queues/status`
- `GET /api/perf`
- `GET /api/items?limit=&offset=&platform=&starred_only=`
- `PATCH /api/items/{id}`
- `POST /api/admin/export`
- `POST /api/admin/import`
- `DELETE /api/admin/reset?confirm=RESET`
- `GET /healthz`

## CLI

```bash
memoryfeed serve
memoryfeed serve-web --host 0.0.0.0 --port 7749
memoryfeed mcp --transport stdio
memoryfeed doctor
memoryfeed doctor --format json
memoryfeed search "that angry cat meme last week"
memoryfeed timeline
memoryfeed feed --mode focus
memoryfeed resurface "Docker networking CNI overlay Cilium"
memoryfeed stats
memoryfeed perf
memoryfeed items --starred
memoryfeed export
memoryfeed import --file ~/.memoryfeed/exports/memoryfeed-export-YYYY-MM-DD.json
memoryfeed models
memoryfeed build-native
memoryfeed build-frontend
memoryfeed reset
```

## Storage Paths

- `~/.memoryfeed/memoryfeed.db`
- `~/.memoryfeed/lancedb/`
- `~/.memoryfeed/images/`
- `~/.memoryfeed/logs/memoryfeed.log`

## Environment Variables

Core mode controls:
- `OFFLINE_ONLY=1|0`
- `MEMORYFEED_AI_PROVIDER=none|gemini|groq|auto`

Provider keys/models:
- `GEMINI_API_KEY=...`
- `GROQ_API_KEY=...`
- `MEMORYFEED_GEMINI_MODEL=gemini-2.5-flash`
- `MEMORYFEED_GROQ_MODEL=qwen/qwen3-32b`
- `MEMORYFEED_GROQ_REWRITE_CAPTIONS=1|0`

Public/admin controls:
- `MEMORYFEED_PUBLIC_MODE=true|false`
- `MEMORYFEED_ADMIN_TOKEN=...`

MCP controls:
- `MEMORYFEED_MCP_MAX_RESULTS=5`
- `MEMORYFEED_MCP_ALLOW_TIMELINE=false`
- `MEMORYFEED_MCP_ALLOW_ACTIVE_FEED=true`
- `MEMORYFEED_MCP_REDACT_OUTPUT=true`

Logging:
- `MEMORYFEED_LOG_LEVEL=DEBUG|INFO|WARNING|ERROR`
- `MEMORYFEED_LOG_FORMAT=plain|json`
- `MEMORYFEED_LOG_FILE=/custom/path/memoryfeed.log`

## Version Mapping

Single source of truth: `memoryfeed/__version__.py`

Current mapping:
- Python package version (pyproject/hatch): `memoryfeed/__version__.py`
- FastAPI app version: `memoryfeed/__version__.py`
- Extension manifests (`chrome`, `firefox`): aligned manually to the same version

## Notes

- `/capture` is non-blocking: vision + embedding run in background queues.
- Search includes short-TTL response cache with automatic invalidation on new captures.
- Semantic query vectors use in-memory cache to reduce repeated model encodes.
- Dedupe key = URL + first 100 chars of text.
