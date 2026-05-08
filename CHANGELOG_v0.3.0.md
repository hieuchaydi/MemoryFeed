# MemoryFeed v0.3.0 Change Summary

Date: 2026-05-08  
Commit base: `d8638cd` (`feat: v0.3.0 extractor reliability and capture dedupe`)

## Scope Implemented

- Extractor reliability improvements for: Facebook, X/Twitter, YouTube, LinkedIn, TikTok.
- Capture payload normalization and schema extension.
- Duplicate reduction via stronger fingerprinting.
- Capture observability/metrics for reliability tracking.
- Test coverage expansion for capture reliability.

## Key Changes

### 1) Capture Schema + Normalization (Backend)

Files:
- `backend/models.py`
- `backend/capture.py`
- `backend/store.py`

Implemented:
- Added fields to capture request/normalized item:
  - `canonical_url`, `post_id`, `media_urls`, `author_name`, `author_handle`, `thumbnail_url`, `source_context`, `quality_flags`, `capture_debug`.
- Added platform-aware canonical URL normalization.
- Added `post_id` extraction from canonical URL.
- Added graceful degradation with `quality_flags` when required fields are missing.

### 2) Dedupe Reliability

Files:
- `backend/capture.py`
- `backend/store.py`

Implemented:
- Dedupe fingerprint upgraded to:
  - `canonical_url + normalized_text + author + 2-hour time bucket`
- Store fallback dedupe logic aligned with same strategy.
- Added DB columns and indexes for new reliability fields (`canonical_url`, `post_id`, etc.).

### 3) Extractor Robustness (Extension)

Files:
- `extension/chrome/content.js`
- `extension/firefox/content.js`
- `extension/chrome/background.js`

Implemented:
- Multi-selector extraction strategy with primary + fallback selectors per platform.
- Canonical URL and post-id aware payload shape.
- Added `capture_debug.selector_used` and missing-field reporting.
- Better TikTok handling for dynamic page behavior.
- Manual capture payload aligned to new schema.

### 4) Observability

File:
- `backend/server.py`

Implemented:
- Structured capture attempt logging.
- In-memory reliability counters per platform.
- `/api/stats` extended with `capture_reliability`:
  - attempts, stored, duplicates, missing_required, success_rate, fail_rate.

### 5) Tests + Version + Docs

Files:
- `tests/test_capture_reliability.py` (new)
- `memoryfeed/__version__.py`
- `extension/chrome/manifest.json`
- `extension/firefox/manifest.json`
- `README.md`
- `DECISIONS.md`

Implemented:
- New tests for:
  - 5-platform happy path normalization,
  - missing-field quality flags,
  - dedupe behavior within time bucket.
- Version bumped to `0.3.0`.
- README/decisions updated to reflect new dedupe strategy.

## Validation Executed

- `python -m unittest discover -s tests -v` -> passed (`11/11`).
- `python -m compileall backend memoryfeed tests` -> passed.
- `node --check` on extension JS files -> passed.

## Deferred (for v0.3.1+)

- Real-world selector tuning based on live DOM snapshots per platform.
- Additional platform-specific edge-case fixtures.
- Optional richer quality scoring beyond missing-field flags.
