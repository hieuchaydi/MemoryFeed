from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.store import Store


def build_export_payload(store: Store) -> dict[str, Any]:
    items = store.export_items()
    return {
        "schema_version": store.schema_version(),
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "items": items,
    }


def _read_items(payload: dict[str, Any] | list[Any]) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if not isinstance(payload, dict):
        return []
    rows = payload.get("items")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def import_payload(store: Store, payload: dict[str, Any] | list[Any]) -> dict[str, Any]:
    inserted = 0
    duplicates = 0
    invalid = 0
    inserted_ids: list[str] = []
    for item in _read_items(payload):
        if not item.get("url"):
            invalid += 1
            continue
        ok, item_id = store.insert_item(item)
        if ok:
            inserted += 1
            if item_id:
                inserted_ids.append(str(item_id))
        else:
            duplicates += 1
    return {
        "inserted": inserted,
        "duplicates": duplicates,
        "invalid": invalid,
        "inserted_ids": inserted_ids,
    }
