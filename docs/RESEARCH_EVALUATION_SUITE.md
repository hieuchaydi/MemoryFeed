# Research Evaluation Suite

MemoryFeed now includes a reproducible research-style evaluation suite.

## Run

```bash
memoryfeed benchmark-suite --limit 10 --iterations 3
```

Artifacts:
- JSON metrics: `backend/benchmarks/runs/research-eval-*.json`
- Markdown summary + performance graph: `backend/benchmarks/runs/research-eval-*.md`

## Metrics

- `latency_ms_p50`: median retrieval latency across benchmark cases.
- `latency_ms_p95`: p95 retrieval latency across benchmark cases.
- `retrieval_precision_at_5`: relevant hits in top-5.
- `memory_hit_quality`: rank-weighted relevance score across top results.
- `token_reduction_percent`: estimated token savings from compressed retrieval context vs raw memory text.
- `pass_rate`: fraction of benchmark cases meeting minimum quality threshold.

## Failure Cases

Failure-case scenarios are versioned in:
- `backend/benchmarks/scenarios/failure_cases.json`

Current failure classes:
- stale memory regression
- contradiction collision
- prompt injection memory leak

## Benchmark Datasets

- Primary scenarios: `backend/benchmarks/scenarios/default_memory_eval.json`
- Extend by adding JSON rows with `query`, `must_include_any`, and `type`.

## Performance Graph

Markdown summaries include Mermaid `xychart-beta` showing recent `latency_ms_p95` trend.

## Comparison Table (Memory Systems)

This is a capability-oriented table from public docs/pages as of May 9, 2026.

| System | Core Memory Model | Local-First Story | Temporal/Contradiction Handling | Reported Perf Signals |
|---|---|---|---|---|
| MemoryFeed | Event + temporal feed + vector + lifecycle state machine | Strong local-first + offline mode + privacy guard | Native lifecycle + conflict records + decay/forget engine | Internal suite now tracks p50/p95, precision@5, hit quality, token reduction |
| Mem0 / OpenMemory | Adaptive memory layer + retrieval/reranking; OpenMemory MCP/local app | Supports self-hosted / local-first modes (product-dependent) | Memory extraction + project-scoped recall; contradiction behavior depends on app policy | Mem0 public materials report token and latency improvements in their benchmarks |
| Zep / Graphiti | Temporal knowledge graph memory layer | Has local/open-source Graphiti and local MCP server options | Strong temporal KG framing with invalidation/history tracking | Zep pages report LongMemEval gains and latency/token improvements |

Source links:
- Mem0 OSS overview: https://docs.mem0.ai/open-source/overview
- Mem0 OpenMemory page: https://mem0.ai/openmemory
- Zep Agent Memory: https://www.getzep.com/product/agent-memory/
- Zep Graphiti OSS: https://www.getzep.com/product/open-source

## Notes

- External benchmark claims from other projects are self-reported by those projects.
- Use the local suite output and your own datasets for apples-to-apples comparisons.
