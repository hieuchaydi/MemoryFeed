# MONITORING.md

## Endpoints
- `/healthz`: liveness.
- `/readyz`: readiness (queues + provider breaker states).
- `/metrics`: Prometheus-compatible text metrics.
- `/api/perf`: detailed runtime diagnostics.

## Key Signals
- queue size (`indexer`, `vision`)
- retry counters and dead-letter counts
- provider circuit breaker state (`open`/`closed`)
- search latency and cache hit ratio (from `/api/perf`)

## Alert Suggestions
- `ready=false` for > 2 minutes.
- dead-letter growth sustained 10+ minutes.
- breaker open > 5 minutes.
- queue_size > 1000 for > 10 minutes.
