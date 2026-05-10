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


def import_payload(payload_or_store: Any, payload: dict[str, Any] | None = None) -> Any:
    if payload is not None:
        return import_payload_to_store(payload_or_store, payload)
    payload_dict = payload_or_store
    warnings: list[str] = []
    version = str(payload_dict.get("schema_version") or "1")
    raw_items = payload_dict.get("items")
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


def build_export_payload(store: Any) -> dict[str, Any]:
    items = store.export_items() if hasattr(store, "export_items") else []
    payload = export_payload(items)
    payload["schema_version"] = max(5, int(str(payload.get("schema_version") or "2")))
    return payload


def import_payload_to_store(store: Any, payload: dict[str, Any]) -> dict[str, Any]:
    items, warnings = import_payload(payload)
    report = {"inserted": 0, "duplicates": 0, "warnings": warnings}
    for item in items:
        ok, _ = store.insert_item(item)
        if ok:
            report["inserted"] += 1
        else:
            report["duplicates"] += 1
    return report
