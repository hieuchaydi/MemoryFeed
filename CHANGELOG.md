# Changelog

## 0.3.1 - 2026-05-09

### Reliability Hardening
- Added migration `0005_reliability_hardening.py` for:
  - `capture_confidence`, `confidence_reasons`
  - `capture_method`, `extractor_version`, `capture_source`, `replay_source`
- Added `backend/import_export.py` with schema-aware import/export payload handling.
- Added configurable dedupe windows:
  - `MEMORY_DEDUPE_WINDOW_HOURS`
  - `MEMORY_PLATFORM_DEDUPE_WINDOWS`
- Added safer URL normalization module (`backend/url_normalization.py`) that preserves meaningful params (for example YouTube timestamp/list) while stripping tracking/session/sensitive params.
- Added deterministic replay mode:
  - `memoryfeed replay <fixture> --deterministic`
  - `memoryfeed extractor test <platform> --deterministic`
- Added capture confidence scoring foundations (`backend/capture_quality.py`) and ranking penalties for low-confidence/incomplete captures.
- Added capture provenance metadata through extension + backend pipeline.
- Added local-only debug endpoint:
  - `GET /api/debug/capture/latest`

### Extension Stability
- Added centralized cleanup lifecycle in content scripts for:
  - `IntersectionObserver`
  - `MutationObserver`
  - timers/intervals/listeners
- Added SPA route-change reset/reinitialize flow to avoid orphan observers.
- Added capture throttling controls:
  - `MEMORY_CAPTURE_MIN_VISIBLE_MS`
  - `MEMORY_CAPTURE_DEBOUNCE_MS`
  - `MEMORY_CAPTURE_MAX_ATTEMPTS_PER_MINUTE`
- Added selector registry validation + safe fallback when selector JSON is malformed.

### Logging & Safety
- Added logging hardening:
  - `MEMORY_LOG_LEVEL`
  - `MEMORY_LOG_MAX_MB`
  - `MEMORY_LOG_ROTATION_COUNT`
- Added log payload sanitization/truncation and sensitive query stripping.

### Test Coverage
- Added/expanded tests for:
  - migration compatibility
  - dedupe windows
  - canonical URL safety
  - capture confidence
  - replay deterministic mode
  - logging safety
  - debug API payload
  - observer cleanup + capture throttling guards
  - selector registry validation checks
  - real-world fixture directories (3 fixtures per platform)

### Deferred to 0.4.0
- Full memory graph UX and visualization
- Semantic clustering workflows
- Advanced ML ranking
- Cross-device sync
- Encrypted vault
- Reinforcement resurfacing

## 0.3.0
- See `CHANGELOG_v0.3.0.md`
