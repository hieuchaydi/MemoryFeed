# Changelog

## 0.4.0 - 2026-05-09

### Added
- Memory intelligence foundations:
  - `related_topics`, `related_entities`, `cluster_id`, `semantic_group`
  - inferred relationship edges in local `memory_links`
- Explainable ranking foundations:
  - `importance_score`, `resurfacing_score`, `recency_score`, `recurrence_score`
  - `ranking_debug` metadata
- Optional semantic near-duplicate layer:
  - `MEMORY_SEMANTIC_DEDUPE=true`
  - `MEMORY_DEDUPE_SIMILARITY_THRESHOLD=0.92`
- Declarative extractor selector registry (`extension/selectors/*.json`)
- Extractor replay tooling:
  - `memoryfeed replay <fixture.html>`
  - `memoryfeed extractor test <platform>`
- Prompt safety boundary:
  - `suspicious_prompt_content` flag
  - MCP output sanitization option (`MEMORY_SANITIZE_PROMPT_CONTENT=true`)
- Sensitive pre-embedding scan:
  - `MEMORY_SKIP_SENSITIVE_EMBEDDING=true`
  - `embedding_skipped_reason` metadata
- Migration framework:
  - `backend/migrations/0001..0004`
  - `memoryfeed migrate`
  - `schema_version` tracking
- Retention and archival foundations:
  - `MEMORY_RETENTION_DAYS`
  - `MEMORY_AUTO_ARCHIVE=true`
  - `MEMORY_ARCHIVE_LOW_SCORE_THRESHOLD`
  - reversible unarchive API
- Reliability benchmark snapshots under `backend/benchmarks/`
- Structured event logging helper with sensitive-data-safe schema

### Changed
- Default search/feed behavior excludes archived memories.
- Capture/store pipeline now computes derived safety/graph/ranking metadata incrementally.
- MCP output pipeline can sanitize untrusted instruction-like text before response redaction.

### Testing
- Added tests for:
  - semantic dedupe
  - replay fixtures
  - migration runner
  - retention/archive reversibility
  - prompt safety
  - sensitive embedding skip
  - ranking behavior
  - benchmarking snapshot generation
  - selector registry validation

### Deferred to 0.4.1
- Full memory graph visualization UI
- Advanced ML ranking pipeline
- Cross-device sync
- Encrypted memory vault
- Reinforcement-based resurfacing

## 0.3.0
- See `CHANGELOG_v0.3.0.md`
