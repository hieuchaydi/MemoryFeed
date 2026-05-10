from __future__ import annotations

from typing import Any

from memoryfeed_core.store import Store


def collect_dirty_items(store: Store, limit: int = 200) -> list[dict[str, Any]]:
    return store.list_dirty_items(limit=limit)

