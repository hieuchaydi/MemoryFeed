# MemoryFeed v1.2.0 Hardening Spec

## Scope
- Close reliability and operability gaps that remained after `v1.1.0`.
- Prioritize user-visible safety: capture correctness signals, namespace semantics clarity, public-mode transport security, and storage lifecycle controls.

## Implemented In This Change

### 1) Capture Health surfaced in Stats
- Problem: `capture_confidence` existed but user could not see low-confidence captures.
- Decision:
  - Add `capture_health` payload in `/api/stats`.
  - Include:
    - `low_confidence`: number of items with `capture_confidence < 0.7`
    - `missing_required`: items with `quality_flags` containing `missing_*`
    - `health_score`: `1 - (low_confidence + missing_required)/total` clamped to `[0,1]`
- UI:
  - Stats page now displays `Capture Health`, `Low Confidence`, `Missing Required`.

### 2) Image Cache lifecycle (quota + maintenance + stats)
- Problem: image cache had no quota and no eviction.
- Decision:
  - Add env `MEMORY_IMAGE_CACHE_MAX_MB` (default `2048`).
  - Add store-level cache stats:
    - `bytes`, `mb`, `files` across `~/.memoryfeed/images` and encrypted media folder.
  - Add LRU-style eviction by file mtime when cache exceeds quota.
  - Run eviction in maintenance cycle.
- API:
  - `/api/stats` now includes `image_cache`.
- UI:
  - Stats page shows image cache footprint.

### 3) Public mode TLS guard
- Problem: public bind could run without TLS termination.
- Decision:
  - On startup, if all true:
    - `MEMORYFEED_PUBLIC_MODE=1`
    - `MEMORYFEED_PUBLIC_REQUIRE_TLS=1` (default true)
    - bind host is non-loopback
    - `MEMORYFEED_TLS_TERMINATED!=1`
  - Then startup fails with explicit runtime error.
- Outcome:
  - Public mode now has enforcement, not only documentation warning.

## Added/Updated Runtime Config
- `MEMORY_IMAGE_CACHE_MAX_MB` (int, default `2048`)
- `MEMORYFEED_PUBLIC_REQUIRE_TLS` (bool, default `true`)
- `MEMORYFEED_TLS_TERMINATED` (bool, default `false`)

## Test Updates
- `tests/test_maintenance.py`:
  - Ensure maintenance summary includes `evicted_images`.
- `tests/test_public_mode_tls.py`:
  - Startup fails in public mode without TLS termination.
  - Startup succeeds when TLS termination flag is set.

## Deferred (Not Implemented In This Patch)
- Namespace authorization model (RBAC per namespace).
- Embedding migration/reindex pipeline (`embedding_model_id`, dual-index rollout).
- Behavior-driven negative feedback loop in resurfacing.
- Graph exploration API/UX.
- Evaluation protocol with human-grounded truth sets.

## Rollout Notes
- For public deployments, set:
  - `MEMORYFEED_PUBLIC_MODE=1`
  - `MEMORYFEED_BIND_HOST=0.0.0.0`
  - `MEMORYFEED_TLS_TERMINATED=1` only when behind HTTPS reverse proxy.
- Tune image cache:
  - `MEMORY_IMAGE_CACHE_MAX_MB=1024` (or lower on constrained disks).
