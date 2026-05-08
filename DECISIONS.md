# Project Decisions (MemoryFeed)

## 1) Product Scope
- Build MemoryFeed as a local capture and indexing system with cloud LLM augmentation.
- Prioritize real-time capture reliability and fast retrieval, while allowing managed model providers for quality.

## 2) Data & Storage
- SQLite in WAL mode for metadata and FTS5 full-text indexing.
- LanceDB for semantic vectors.
- Local image cache at `~/.memoryfeed/images` to avoid dead remote image URLs.
- All user data stays on local machine.

## 3) Architecture
- Browser Extension (capture)
- FastAPI Backend (ingest, queues, APIs)
- React + Vite Frontend (operator console)
- Optional Native C++ Acceleration layer (pybind11)

## 4) Ingestion Strategy
- Extension captures content after dwell > 3 seconds.
- Normalize capture payload to canonical URL + post id + quality flags before insert.
- Deduplicate by `canonical_url + normalized_text + author + 2-hour time bucket` fingerprint.
- `/capture` endpoint returns quickly and never waits for heavy jobs.

## 5) Async Processing
- Vision pipeline (Gemini API) runs in background queue.
- Optional caption rewrite/summarization (Groq Qwen) runs in background queue.
- Embedding pipeline (`paraphrase-multilingual-MiniLM-L12-v2`) runs in background queue.
- On failures (network/image/model unavailable), keep item persisted and continue.

## 6) Search Strategy
- Hybrid search = FTS5 BM25 + semantic vector search.
- Merge ranking with Reciprocal Rank Fusion:
  - `score = 1/(rank_fts + 60) + 1/(rank_sem + 60)`
- Return compact card-ready results with thumbnail and excerpt.

## 7) Active Memory Strategy
- Memories carry `heat`, `last_surfaced`, `surfaced_count`, and `archived_at`.
- Daily decay cools memories that have not been surfaced recently.
- Related new captures warm older memories through background hybrid retrieval.
- `/api/feed` ranks by heat, recency, dwell, star state, resurfacing gap, and mode.
- `/api/resurface` is the ambient integration contract for browser/VS Code/Raycast/MCP context.

## 8) Frontend Direction
- Use React + Vite as primary UX (not server-rendered templates).
- API-first contract under `/api/*`.
- FastAPI serves built SPA in production mode.

## 9) Performance Direction
- Default path: pure Python (portable).
- Fast path: native C++ module (`memoryfeed_native`) when available.
- Native module currently accelerates:
  - text normalization
  - RRF score fusion
  - RRF top-k ranking output (`rrf_topk`) to reduce Python sorting overhead
- Python runtime adds:
  - short-TTL search response cache
  - semantic query embedding cache (LRU + TTL)
  - lower-lock insert path (`INSERT OR IGNORE`) for dedupe-heavy ingestion
- Missing native module must never break runtime.

## 10) Performance Observability
- Add `/api/perf` endpoint for runtime diagnostics:
  - search cache hit/miss/eviction
  - search latency summary and last-stage timings
  - queue pressure and native status
- Add CLI command `memoryfeed perf` for quick operator checks.

## 11) Operability
- One-command startup scripts:
  - Windows: `quickstart.ps1`
  - Linux/macOS: `quickstart.sh`
- CLI includes operational commands for serve, stats, model checks, frontend build, native build.

## 12) Security & Privacy
- Outbound inference is allowed only to configured providers (Gemini/Groq).
- No telemetry.
- CORS limited to local frontend and browser extension origins.

## 13) Deferred Decisions
- Distributed multi-user mode: deferred.
- Remote sync and multi-device replication: deferred.
- GPU-specific native acceleration roadmap: deferred until baseline usage metrics.
