# Changelog

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
