# MemoryFeed Infrastructure Blueprint

This document defines the production-grade evolution of MemoryFeed from a vector wrapper into long-term memory infrastructure for AI systems.

## 1. Memory Lifecycle Architecture

### 1.1 Canonical Memory State Machine

Each memory item has an immutable `event_id` and mutable `memory_id` state:

1. `captured`
2. `normalized`
3. `summarized`
4. `indexed`
5. `reinforced`
6. `decaying`
7. `archived`
8. `forgotten`

Never update raw capture in-place. Append new facts/events and materialize current view.

### 1.2 Lifecycle Engine Design

Core services:
- `Capture Ingestor`: validates schema, computes source trust, extracts entities/time/url.
- `Summarizer`: creates layered summaries (`s_short`, `s_medium`, `s_long`) with provenance spans.
- `Compressor`: rollups by window/topic/persona (day/week/month + thematic cluster).
- `Reinforcement Engine`: boosts memory strength when reused, cited, confirmed, or user-starred.
- `Decay Engine`: applies half-life by class (task, preference, fact, ephemeral).
- `Forget Engine`: policy-based purge/anonymize/tombstone by TTL + legal + user controls.
- `Merge Engine`: dedupe + co-reference merge while preserving source lineage.
- `Conflict Resolver`: detects contradictory claims and stores both with confidence and freshness.

Execution model:
- Event log + idempotent workers.
- Priority queues: `hot` (capture/retrieval path), `warm` (summaries), `cold` (compaction).
- SLA targets: ingest P95 < 300ms, retrieval P95 < 500ms, background lag < 2 min.

### 1.3 Core Data Model (minimum)

- `memory_event`: immutable captured unit with `content_hash`, `source`, `captured_at`.
- `memory_node`: consolidated memory object with type (`fact`, `intent`, `task`, `preference`, `episode`).
- `memory_edge`: graph links (`supports`, `contradicts`, `derived_from`, `same_as`).
- `memory_strength`: dynamic score components (importance, reuse_count, confirmations, decay_value).
- `memory_versions`: summary/compression versions + provenance spans.
- `memory_tombstone`: deletion metadata and reason (`ttl`, `user_delete`, `privacy_policy`).

### 1.4 Conflict Resolution Policy

Store contradiction as first-class relation:
- Do not overwrite prior claim.
- Keep both claims with `valid_from`, `valid_to`, `confidence`, `source_reliability`.
- Retrieval returns either:
  - best current claim, or
  - explicit ambiguity block when confidence gap < threshold.

Resolution score example:

`final_confidence = src_reliability * freshness_weight * corroboration_factor * user_confirmation`

### 1.5 Merge Strategy

Three gates before merge:
1. Deterministic gate: canonical URL/entity/time overlap.
2. Semantic gate: embedding similarity above adaptive threshold by type.
3. Safety gate: contradiction risk and identity collision check.

If uncertain: soft-link (`possibly_same`) instead of hard merge.

## 2. Memory Evaluation Framework

## 2.1 Benchmark Suites

1. `LT-Recall`: delayed retrieval across 1d/7d/30d/90d intervals.
2. `Consistency`: same query across time snapshots should preserve stable facts.
3. `Hallucination Shield`: measure unsupported claims in answer with/without memory.
4. `Staleness Handling`: old facts replaced by new facts without regression.
5. `Contradiction Handling`: explicitly detect and represent conflicting memories.

### 2.2 Metrics

- Recall@K by horizon (`R@5_30d`, `R@10_90d`).
- Temporal nDCG (time-aware relevance gain).
- Contradiction Precision/Recall/F1.
- Stale Override Rate (newer-correct fact selected over stale fact).
- Grounded Answer Rate (fraction of answer spans traceable to memory citations).
- Unsupported Claim Rate (lower is better).
- Memory Drift Index (answer change for invariant queries).

### 2.3 Dataset Design

- Synthetic long-horizon conversations with controlled fact mutations.
- Realistic browser-capture streams (social/news/docs/tasks) with timestamps.
- Contradiction packets (same entity, changing attribute values).
- Privacy-sensitive samples for redaction/isolation validation.

Store dataset versioned as:
- `benchmarks/scenarios/*.jsonl`
- `benchmarks/labels/*.json`
- `benchmarks/manifests/*.yaml`

### 2.4 Evaluation Methodology

- Fixed replay seed, deterministic retrieval mode for benchmark runs.
- A/B compare retrieval policies on same memory snapshot.
- Weekly regression gate in CI:
  - block merge if `R@10_30d` drops > 3%
  - block merge if unsupported claims increase > 1.5%

## 3. Temporal Memory Visualization

### 3.1 Timeline UI

Views:
- event stream (raw captures)
- memory stream (merged semantic memories)
- resolution stream (conflict updates)

Interactions:
- scrub by time window
- filter by entity/topic/source trust
- jump-to-retrieval-context

### 3.2 Memory Heatmap

Axes:
- X: time buckets
- Y: topic/entity clusters
- Color: access frequency * reinforcement strength

Use this to detect forgotten-but-important zones and overfit zones.

### 3.3 Reinforcement Graph

Nodes: memory items.
Edges: retrieval/use references.
Weight: reinforcement delta.

Surface central memories and isolate noisy hubs.

### 3.4 Aging Visualization

Per memory card:
- age curve
- current decay coefficient
- next policy action (retain/archive/forget)

### 3.5 Retrieval Trace UI

For every answer, show:
- candidate set
- reranking feature contributions
- selected memories with citations
- suppressed candidates (duplicate/stale/conflict)

## 4. Local-First Privacy Architecture

### 4.1 Offline Guarantees

- Hard network deny mode (`OFFLINE_ONLY=1`) enforced in runtime guard, not only config.
- Boot-time self-test verifies no provider keys are active in local-only mode.
- Audit log event `network_call_blocked` when any external call is attempted.

### 4.2 Encryption Strategy

- At rest: XChaCha20-Poly1305 per memory shard, data key wrapped by device master key.
- Key hierarchy:
  - Master Key (OS keystore/TPM)
  - Data Encryption Keys (rotatable)
  - Per-export one-time key
- Rotate DEK quarterly or on compromise event.

### 4.3 Local-Only Mode Controls

- Disable cloud providers and remote embedding endpoints.
- Disable telemetry by default.
- UI privacy badge: `Local-Only Verified` + last verification timestamp.

### 4.4 Extension Privacy Model

- Capture minimization: only fields needed for memory purpose.
- On-device redaction before persistence (PII/token/email/phone patterns).
- Domain allowlist and per-domain capture toggles.

### 4.5 Memory Isolation

Support isolated profiles:
- `work`, `personal`, `project-x` namespaces.
- Separate encryption context and index per namespace.
- No cross-namespace retrieval unless explicit bridge policy.

## 5. Retrieval Intelligence

### 5.1 Hybrid Ranking Formula

`score = w_sem*semantic + w_temp*temporal + w_imp*importance + w_ctx*context + w_rel*source_reliability - w_dup*dup_penalty - w_stale*stale_penalty`

Adaptive weights by query intent (`fact_lookup`, `status`, `preference`, `episodic`).

### 5.2 Recency vs Importance

- Fast-decay for transient noise (social chatter).
- Slow-decay for user preferences, long-lived tasks, verified facts.
- Reinforcement can offset decay up to cap.

### 5.3 Semantic Reinforcement

Boost memories when:
- explicitly cited in successful answer
- user confirms relevance
- appears in repeated query neighborhoods

Decay reinforcement when not used for long horizon.

### 5.4 Duplicate Suppression

- Near-duplicate clustering at ingest.
- Retrieval-time MMR/diversity rerank.
- Keep one representative + optional `more_like_this` expansion.

### 5.5 Contextual Prioritization

Build query context vector from:
- active task window
- recent conversation turns
- user persona/profile namespace

Use contextual constraints before final rerank.

## 6. Research-Level Documentation Package

Create `docs/research/` with:

1. `architecture-overview.md`
- C4 context/container/component diagrams.

2. `lifecycle-engine.md`
- state machine + worker orchestration + failure modes.

3. `retrieval-intelligence.md`
- ranking features, equations, ablations.

4. `evaluation-protocol.md`
- benchmark scenarios, metrics, pass/fail gates.

5. `privacy-threat-model.md`
- adversaries, attack paths, mitigations, residual risk.

Diagram suggestions:
- memory pipeline sequence diagram
- lifecycle flowchart (capture -> forget)
- contradiction handling decision tree
- retrieval trace waterfall

## 7. Browser Extension Hardening

### 7.1 Stable Permission Model

- Use exact host permissions only; no wildcards.
- Split optional permissions by platform connector.
- Runtime prompt when enabling new domain capture.

### 7.2 Minimal Capture Strategy

- Dwell threshold + explicit user action option.
- Capture structured metadata, not full DOM by default.
- Sample media lazily only when needed.

### 7.3 Onboarding UX

- Step 1: privacy modes explained with examples.
- Step 2: choose domains to capture.
- Step 3: choose namespace (`work/personal`).
- Step 4: local-only validation check.

### 7.4 Sync Strategy

- Default: no cloud sync.
- Optional encrypted bundle export/import between devices.
- Conflict handling via event-log replay and deterministic merge.

### 7.5 Local Encryption in Extension Flow

- Encrypt payload before writing to local persistence queue.
- Zeroize plaintext buffers after transfer.
- Rate-limit and integrity-sign extension->backend messages.

## 8. Implementation Roadmap

### Phase 1 (2-4 weeks)
- Introduce lifecycle state machine tables and event log.
- Add contradiction edges and stale handling in retrieval.
- Add retrieval trace endpoint.

### Phase 2 (4-6 weeks)
- Build benchmark harness and CI regression gates.
- Implement reinforcement/decay policy engine.
- Ship temporal heatmap + reinforcement graph.

### Phase 3 (4-8 weeks)
- Encryption key hierarchy + namespace isolation.
- Extension permission hardening + onboarding redesign.
- Publish research docs with ablation and tradeoff analysis.

## 9. Production Readiness Checklist

- Deterministic migrations and rollback tested.
- Replayable event log with idempotent workers.
- Queue retry/backoff + dead-letter observability enabled for asynchronous workers.
- External provider circuit breakers enabled for caption/summarization calls.
- API rate limiting and readiness probe (`/readyz`) enabled.
- SLO dashboards for ingest/retrieval/background lag.
- Benchmark gate integrated in CI.
- Threat model reviewed and signed off.
- Disaster recovery drill (backup/restore) validated.
