# memoryfeed-core

Standalone core library extracted from MemoryFeed for easier third-party integration.

## Install

```bash
pip install -e ./memoryfeed-core
```

## Quick usage

```python
from memoryfeed_core import Store, IndexerService, Searcher

store = Store()
indexer = IndexerService(store)
searcher = Searcher(store, indexer)
```

## Scope

- Capture normalization and safety checks
- Storage, migrations, retention, and lifecycle
- Indexing, semantic retrieval, reranking, and interest feed
- FastAPI server app and MCP server runtime

MCP RAG context tool:
- `build_memory_context(query, limit=8, days_back=None, max_context_chars=4000)`
