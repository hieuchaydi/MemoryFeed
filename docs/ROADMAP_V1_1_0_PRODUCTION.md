# MemoryFeed v1.1.0 Production Roadmap

## Current State (after commit-32 plus recent upgrades)

Strengths:
- Local-first capture/search pipeline with offline mode.
- Lifecycle foundation + namespace isolation + retrieval evaluation suite.
- Security controls: admin token, MCP redaction, sensitive-content suppression.

Largest gaps to full production:
- No true at-rest encryption for SQLite/image cache yet.
- Queue reliability needed explicit retry/dead-letter policy.
- External provider calls lacked circuit breaker protection.
- Missing readiness probe and API rate limiting guard.
- CI does not yet gate on benchmark regressions.

## v1.1.0 Scope

### P0 (must-have)
1. Queue resilience: retry + exponential backoff + dead-letter counters.
2. Provider circuit breaker for Gemini/Groq calls.
3. API rate limiting and `/readyz` readiness probe.
4. Structured observability extension for queue/provider states.

### P1 (high priority)
1. At-rest encryption design + implementation (SQLCipher or encrypted blob layer).
2. Key management integration (OS keyring/TPM wrapper).
3. Benchmark CI regression gates (latency/precision/hit-quality/token-reduction).
4. Extension reliability suite (fixture replay on selector changes).

### P2 (next)
1. Frontend production visualizations (heatmap/aging/reinforcement graph with drilldown).
2. Namespace migration tooling and onboarding UX.
3. Context-aware MCP retrieval profiles.

## Effort Estimate

- P0: 3-5 engineering days.
- P1: 2-3 weeks.
- P2: 2 weeks.

## Release Exit Criteria

- Unit/integration tests green.
- Queue dead-letter visible in `/api/perf` and `/readyz`.
- Provider breaker states visible in `/api/perf` and `/readyz`.
- Rate limiting enforced on `/api/*` with configurable env.
- Docs updated: README + SECURITY + Blueprint.
