from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from memoryfeed_core.capture import canonicalize_url, detect_platform, make_dedupe_key
from memoryfeed_core.store import IMAGE_CACHE_DIR, Store


@dataclass
class VerifyReport:
    malformed_records: list[str]
    invalid_canonical_urls: list[str]
    broken_references: list[str]
    duplicate_fingerprints: list[str]
    missing_timestamps: list[str]
    invalid_schema_fields: list[str]
    missing_embedding: list[str]
    orphan_relationships: list[str]
    repaired: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "malformed_records": self.malformed_records,
            "invalid_canonical_urls": self.invalid_canonical_urls,
            "broken_references": self.broken_references,
            "duplicate_fingerprints": self.duplicate_fingerprints,
            "missing_timestamps": self.missing_timestamps,
            "invalid_schema_fields": self.invalid_schema_fields,
            "missing_embedding": self.missing_embedding,
            "orphan_relationships": self.orphan_relationships,
            "repaired": self.repaired,
        }


def verify_store(store: Store, repair: bool = False) -> VerifyReport:
    rows = store.all_items()
    raw_fields = _load_raw_schema_fields(store)
    report = VerifyReport([], [], [], [], [], [], [], [], [])
    dedupe_seen: dict[str, str] = {}
    all_ids = {str(i.get("id")) for i in rows if i.get("id")}

    for item in rows:
        item_id = str(item.get("id") or "")
        if not item_id or not item.get("url") or not item.get("platform"):
            report.malformed_records.append(item_id or "<missing-id>")
        canonical = str(item.get("canonical_url") or "")
        if not _valid_url(canonical):
            report.invalid_canonical_urls.append(item_id)
        if not _parse_iso(str(item.get("captured_at") or "")):
            report.missing_timestamps.append(item_id)

        dedupe = str(item.get("dedupe_key") or "")
        if dedupe:
            prev = dedupe_seen.get(dedupe)
            if prev and prev != item_id:
                report.duplicate_fingerprints.append(f"{prev}:{item_id}")
            dedupe_seen[dedupe] = item_id

        if not bool(item.get("embedding_done")) and not bool(item.get("embedding_skipped")):
            report.missing_embedding.append(item_id)

        raw_item = raw_fields.get(item_id, {})
        for field in ("related_topics", "related_entities", "quality_flags", "sensitivity_reasons"):
            raw_value = raw_item.get(field)
            if raw_value in (None, ""):
                continue
            if not _is_json_list(raw_value):
                report.invalid_schema_fields.append(f"{item_id}:{field}")

        source_context = str(item.get("source_context") or "")
        if source_context.startswith("item:"):
            ref = source_context.split(":", 1)[-1].strip()
            if ref and ref not in all_ids:
                report.orphan_relationships.append(f"{item_id}->{ref}")

        for path in item.get("image_cache_paths") or []:
            if not _valid_cache_ref(str(path)):
                report.broken_references.append(f"{item_id}:{path}")

        if repair:
            changed_fields: dict[str, Any] = {}
            if not canonical or not _valid_url(canonical):
                platform = detect_platform(str(item.get("url") or ""), fallback=str(item.get("platform") or "unknown"))
                changed_fields["canonical_url"] = canonicalize_url(str(item.get("url") or ""), platform=platform)
            rebuilt = make_dedupe_key(
                str(changed_fields.get("canonical_url") or item.get("canonical_url") or item.get("url") or ""),
                str(item.get("text_content") or ""),
                platform=str(item.get("platform") or "unknown"),
                author_name=str(item.get("author_name") or item.get("author") or ""),
                captured_at_iso=str(item.get("captured_at") or ""),
            )
            if rebuilt and rebuilt != dedupe:
                changed_fields["dedupe_key"] = rebuilt
            if not _parse_iso(str(item.get("captured_at") or "")):
                changed_fields["captured_at"] = datetime.now(timezone.utc).isoformat()
            cache_paths = [p for p in (item.get("image_cache_paths") or []) if _valid_cache_ref(str(p))]
            if cache_paths != (item.get("image_cache_paths") or []):
                changed_fields["image_cache_paths"] = cache_paths
            if changed_fields:
                store.update_integrity_fields(item_id, changed_fields)
                report.repaired.append(item_id)
    return report


def _parse_iso(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def _valid_url(value: str) -> bool:
    if not value:
        return False
    try:
        parsed = urlparse(value)
        return bool(parsed.scheme and parsed.netloc)
    except Exception:
        return False


def _valid_cache_ref(value: str) -> bool:
    if not value:
        return False
    try:
        if value.startswith("/images/"):
            return True
        from pathlib import Path

        p = Path(value)
        return p.exists() and p.parent.resolve() == IMAGE_CACHE_DIR.resolve()
    except Exception:
        return False


def _load_raw_schema_fields(store: Store) -> dict[str, dict[str, Any]]:
    conn = store._connect()  # pylint: disable=protected-access
    try:
        rows = conn.execute(
            """
            SELECT id, related_topics, related_entities, quality_flags, sensitivity_reasons
            FROM items
            """
        ).fetchall()
        out: dict[str, dict[str, Any]] = {}
        for row in rows:
            out[str(row["id"])] = {
                "related_topics": row["related_topics"] if "related_topics" in row.keys() else None,
                "related_entities": row["related_entities"] if "related_entities" in row.keys() else None,
                "quality_flags": row["quality_flags"] if "quality_flags" in row.keys() else None,
                "sensitivity_reasons": row["sensitivity_reasons"] if "sensitivity_reasons" in row.keys() else None,
            }
        return out
    finally:
        conn.close()


def _is_json_list(raw: Any) -> bool:
    if not isinstance(raw, str):
        return False
    import json

    try:
        parsed = json.loads(raw)
    except Exception:
        return False
    return isinstance(parsed, list)

