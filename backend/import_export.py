from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

SCHEMA_VERSION = "2"


def export_payload(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "items": items,
    }


def import_payload(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    version = str(payload.get("schema_version") or "1")
    raw_items = payload.get("items")
    if not isinstance(raw_items, list):
        warnings.append("invalid_items_payload")
        return [], warnings

    normalized: list[dict[str, Any]] = []
    for idx, item in enumerate(raw_items):
        if not isinstance(item, dict):
            warnings.append(f"skipped_non_object_item:{idx}")
            continue
        if not item.get("url"):
            warnings.append(f"skipped_missing_url:{idx}")
            continue
        if version == "1" and not item.get("canonical_url"):
            item = dict(item)
            item["canonical_url"] = item.get("url")
        normalized.append(item)
    if version not in {"1", SCHEMA_VERSION}:
        warnings.append(f"unknown_schema_version:{version}")
    return normalized, warnings
