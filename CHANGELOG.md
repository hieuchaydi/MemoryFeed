# Changelog

## v1.2.0 - Hardening Patch (2026-05-11)

### Added
- Public mode TLS startup guard:
  - Startup now fails when running public bind without TLS termination flag.
  - New env controls: `MEMORYFEED_PUBLIC_REQUIRE_TLS`, `MEMORYFEED_TLS_TERMINATED`.
- Image cache lifecycle controls:
  - New env `MEMORY_IMAGE_CACHE_MAX_MB` for cache quota.
  - LRU-style cache eviction integrated into maintenance cycle.
  - `/api/stats` now reports image cache usage (`bytes`, `mb`, `files`).
- Capture health visibility:
  - `/api/stats` now includes `capture_health` (`low_confidence`, `missing_required`, `health_score`).
  - Stats frontend now shows Capture Health and image cache cards.
- Documentation:
  - Added `docs/V1_2_0_HARDENING_SPEC.md`.

### Changed
- Maintenance summary now includes `evicted_images`.

### Tests
- Updated maintenance test to assert `evicted_images`.
- Added `tests/test_public_mode_tls.py` for TLS enforcement behavior.

## v0.4.0 - Reliability Hardening (2026-05-09)

### Added
- Storage integrity verification and repair CLI:
  - `memoryfeed verify`
  - `memoryfeed verify --repair`
- Transactional atomic write path with rollback safety on interrupted/failed writes.
- Explainable search debug metadata (ranking factors, match fields, penalties).
- Diversity-aware reranking to suppress near-duplicate result floods.
- Local heuristic noise classification (`noise_score`, `low_signal_reason`).
- Memory decay lifecycle metadata (`decay_score`, `aging_state`) with configurable half-life.
- Lightweight memory graph fields (`related_topics`, `related_entities`, `semantic_group`).
- Prompt-injection risk scoring and MCP untrusted-content sanitization boundary.
- Sensitive content classification with configurable search suppression and embedding skip.
- Background maintenance scheduler for fingerprint rebuild, index compaction, log cleanup, and ranking recompute.
- Incremental indexing support via dirty-state tracking.
- Versioned import/export payload (`schema_version`) and warnings-first compatibility handling.
- Reliability dashboard foundation payload in `/api/stats`.
- Debug explainability endpoint for item-level duplicate/archival/confidence traces.

### Changed
- Version aligned to `0.4.0` for backend package, frontend package, and browser extensions.
- Search default behavior excludes archived memories and (by default) high-sensitivity content.

### Deferred to v0.4.1+
- Full graph visualization UI.
- Cross-device sync.
- Encrypted local vault.
- Advanced semantic clustering.
- Reinforcement-based resurfacing.
- Collaborative memory sharing.
