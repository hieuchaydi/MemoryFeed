# MemoryFeed v1.2.0

Release date: 2026-05-11

## Highlights
- Public mode now enforces TLS readiness at startup.
- Capture quality is visible in Stats via a new Capture Health section.
- Image cache now has quota controls, maintenance eviction, and usage stats.

## What Changed

### Security / Public Mode
- Added startup guard for public deployments:
  - If `MEMORYFEED_PUBLIC_MODE=1` and server binds to non-loopback host,
  - startup requires `MEMORYFEED_TLS_TERMINATED=1` unless TLS requirement is explicitly disabled.
- New envs:
  - `MEMORYFEED_PUBLIC_REQUIRE_TLS` (default: `true`)
  - `MEMORYFEED_TLS_TERMINATED` (default: `false`)

### Reliability / Capture Health
- `/api/stats` now includes:
  - `capture_health.low_confidence`
  - `capture_health.missing_required`
  - `capture_health.health_score`
- Stats UI now shows:
  - Capture Health percentage
  - Low-confidence capture count
  - Missing-required-fields count

### Storage Lifecycle / Image Cache
- Added configurable cache quota:
  - `MEMORY_IMAGE_CACHE_MAX_MB` (default: `2048`)
- Maintenance cycle now enforces image cache size limit with mtime-based eviction.
- `/api/stats` now includes `image_cache` usage (`bytes`, `mb`, `files`).
- Stats UI now displays image cache footprint.

## Testing
- Added `tests/test_public_mode_tls.py`:
  - verifies startup failure without TLS termination in public mode
  - verifies startup success with TLS termination flag
- Updated `tests/test_maintenance.py` to validate `evicted_images` in maintenance summary.

## Upgrade Notes
- Public deployments behind reverse proxy should set:
  - `MEMORYFEED_PUBLIC_MODE=1`
  - `MEMORYFEED_BIND_HOST=0.0.0.0`
  - `MEMORYFEED_TLS_TERMINATED=1`
- Tune image cache for disk constraints:
  - `MEMORY_IMAGE_CACHE_MAX_MB=1024` (or lower)
