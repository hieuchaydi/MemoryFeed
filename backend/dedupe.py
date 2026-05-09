from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

from backend.embeddings import build_semantic_text, cosine_similarity, hash_embedding
from backend.runtime_config import dedupe_window_hours_for_platform


@dataclass
class SemanticDuplicateMatch:
    duplicate_id: str
    similarity: float
    reason: str


def infer_domain(url: str | None) -> str:
    if not url:
        return ""
    try:
        parsed = urlparse(url)
    except Exception:
        return ""
    host = (parsed.netloc or "").lower().strip()
    if host.startswith("www."):
        host = host[4:]
    return host


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def dedupe_bucket(captured_at_iso: str | None, platform: str | None = None) -> str:
    dt = _parse_iso(captured_at_iso)
    if dt is None:
        dt = datetime.now(timezone.utc)
    hours = dedupe_window_hours_for_platform(platform)
    bucket_seconds = max(60, int(hours) * 60 * 60)
    return str(int(dt.timestamp() // bucket_seconds))


def _candidate_rows(conn, item: dict[str, Any], window_days: int = 180) -> list[dict[str, Any]]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    domain = infer_domain(item.get("canonical_url") or item.get("url"))
    platform = str(item.get("platform") or "unknown")
    author = str(item.get("author_name") or item.get("author") or "")

    where_parts = ["archived_at IS NULL", "captured_at >= ?"]
    params: list[Any] = [cutoff.isoformat()]
    if domain:
        where_parts.append("url_domain = ?")
        params.append(domain)
    else:
        where_parts.append("platform = ?")
        params.append(platform)
    if author:
        where_parts.append("(author_name = ? OR author = ?)")
        params.extend([author, author])

    query = f"""
        SELECT id, text_content, image_captions, tags, author_name, author, captured_at, semantic_group
        FROM items
        WHERE {" AND ".join(where_parts)}
        ORDER BY captured_at DESC
        LIMIT 240
    """
    rows = conn.execute(query, params).fetchall()
    out: list[dict[str, Any]] = []
    for row in rows:
        out.append(
            {
                "id": row["id"],
                "text_content": row["text_content"] or "",
                "image_captions": json.loads(row["image_captions"] or "[]"),
                "tags": json.loads(row["tags"] or "[]") if "tags" in row.keys() and row["tags"] else [],
                "author_name": row["author_name"] if "author_name" in row.keys() else None,
                "author": row["author"],
                "captured_at": row["captured_at"],
                "semantic_group": row["semantic_group"] if "semantic_group" in row.keys() else None,
            }
        )
    return out


def find_semantic_duplicate(conn, item: dict[str, Any], threshold: float) -> SemanticDuplicateMatch | None:
    source_text = build_semantic_text(item)
    if not source_text:
        return None

    src_vec = hash_embedding(source_text)
    if not any(src_vec):
        return None

    newest_match: SemanticDuplicateMatch | None = None
    newest_dt: datetime | None = None
    for candidate in _candidate_rows(conn, item):
        cand_text = build_semantic_text(candidate)
        if not cand_text:
            continue
        sim = cosine_similarity(src_vec, hash_embedding(cand_text))
        if sim < threshold:
            continue

        reason = f"semantic_similarity:{sim:.4f}"
        cand_dt = _parse_iso(candidate.get("captured_at"))
        if newest_match is None:
            newest_match = SemanticDuplicateMatch(
                duplicate_id=str(candidate["id"]),
                similarity=float(sim),
                reason=reason,
            )
            newest_dt = cand_dt
            continue

        if cand_dt and (newest_dt is None or cand_dt > newest_dt):
            newest_match = SemanticDuplicateMatch(
                duplicate_id=str(candidate["id"]),
                similarity=float(sim),
                reason=reason,
            )
            newest_dt = cand_dt

    return newest_match
