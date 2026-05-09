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
- Extension captures content after configurable visibility dwell/debounce/rate-limit thresholds.
- Normalize capture payload to canonical URL + post id + quality flags before insert.
- Deduplicate by `canonical_url + normalized_text + author + configurable time bucket` fingerprint.
- `/capture` endpoint returns quickly and never waits for heavy jobs.

## 4.1) Reliability Hardening (v0.3.1)
- Add centralized lifecycle cleanup in content scripts for observers/intervals/timeouts.
- Route-change reinitialization is required to avoid orphan observers on SPA feeds.
- Capture payload includes provenance metadata (`capture_method`, `extractor_version`, `capture_source`) and confidence (`capture_confidence`, `confidence_reasons`).
- Keep selector registry failures non-fatal: validate schema, warn, and fallback to defaults.

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
- Search explainability is opt-in (`--debug` / `debug=true`) and returns ranking factors without raw sensitive payload dumps.
- Diversity reranking is enabled by default with `MEMORY_SEARCH_DIVERSITY=true` to avoid near-duplicate result floods.

## 7) Active Memory Strategy
- Memories carry `heat`, `last_surfaced`, `surfaced_count`, and `archived_at`.
- Daily decay cools memories that have not been surfaced recently.
- Related new captures warm older memories through background hybrid retrieval.
- `/api/feed` ranks by heat, recency, dwell, star state, resurfacing gap, and mode.
- `/api/resurface` is the ambient integration contract for browser/VS Code/Raycast/MCP context.
- Decay score and aging state are stored (`decay_score`, `aging_state`) and recomputed by maintenance/decay loops.

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
- CLI includes `memoryfeed verify` and `memoryfeed verify --repair` for local data integrity checks/repairs.

## 12) Security & Privacy
- Outbound inference is allowed only to configured providers (Gemini/Groq).
- No telemetry.
- CORS limited to local frontend and browser extension origins.
- Prompt-risk and sensitivity classification run locally at ingestion time.
- Sensitive memories can be excluded from search and embedding (`MEMORY_HIDE_SENSITIVE_FROM_SEARCH`, `MEMORY_SKIP_SENSITIVE_EMBEDDING`).
- MCP output can sanitize untrusted prompt-like content under redaction policy.

## 13) Data Integrity & Maintenance
- SQLite writes use explicit transactional boundaries with rollback-on-failure semantics for capture/update paths.
- Storage records carry dirty-index state to support incremental reindexing.
- Background local maintenance handles fingerprint rebuild, index compaction, log cleanup, and decay/ranking recomputation.
- Export format is versioned (`schema_version`) with backward-compatible import and warnings-first recovery behavior.

## 14) Deferred Decisions
- Distributed multi-user mode: deferred.
- Remote sync and multi-device replication: deferred.
- GPU-specific native acceleration roadmap: deferred until baseline usage metrics.

## 14) Memory Graph Foundations (v0.4.0)
- Keep storage on SQLite; do not introduce a graph database yet.
- Add optional item-level semantic fields (`related_topics`, `related_entities`, `cluster_id`, `semantic_group`).
- Persist inferred edges in local `memory_links` table for replay/debug and future graph UI.
- Relationship inference stays heuristic and explainable (domain, topic/entity recurrence, local similarity).

## 15) Explainable Ranking Foundations (v0.4.0)
- Add four explicit scores: `importance_score`, `resurfacing_score`, `recency_score`, `recurrence_score`.
- Keep scoring heuristic-based for now; no mandatory ML ranking service.
- Store `ranking_debug` metadata for auditability and future tuning.

## 16) Dedupe Strategy Update (v0.4.0)
- Preserve fingerprint dedupe as first layer.
- Add optional semantic near-duplicate layer (`MEMORY_SEMANTIC_DEDUPE=true`) with configurable threshold.
- Keep all dedupe local-only and offline-capable.

## 17) Extractor Maintainability (v0.4.0)
- Move selector logic toward declarative JSON configs per platform.
- Keep hardcoded in-script fallback selectors to avoid regressions when config loading fails.
- Add fixture replay tooling (`memoryfeed replay`, `memoryfeed extractor test`) for DOM drift regression checks.

## 18) Safety and Privacy Boundary (v0.4.0)
- Treat captured text as untrusted input.
- Add prompt-injection heuristic flag (`suspicious_prompt_content`) instead of destructive deletion.
- Add pre-embedding sensitive scan; skip embedding when configured, but still store local raw capture.
- MCP output can sanitize suspicious instruction-like text while preserving useful context.

## 19) Schema Evolution (v0.4.0)
- Introduce numbered migration framework under `backend/migrations/`.
- Track `schema_version` in DB `meta` table.
- Keep migrations idempotent and backward-compatible.

## 20) Retention and Archival (v0.4.0)
- Introduce reversible archival (no destructive auto-delete).
- Default search/feed excludes archived entries.
- Track `archive_reason` for explainability and operations.
