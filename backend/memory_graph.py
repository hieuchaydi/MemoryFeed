from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

from backend.embeddings import build_semantic_text, cosine_similarity, hash_embedding, tokenize

_HASHTAG_RE = re.compile(r"#([A-Za-z0-9_]{2,40})")
_HANDLE_RE = re.compile(r"@([A-Za-z0-9_.-]{2,40})")
_ENTITY_RE = re.compile(r"\b([A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,}){0,2})\b")


def infer_url_domain(url: str | None) -> str:
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


def extract_topics(text: str, tags: list[str] | None = None, max_topics: int = 8) -> list[str]:
    content = text or ""
    seen: list[str] = []

    for match in _HASHTAG_RE.findall(content):
        topic = match.lower().strip("_-")
        if topic and topic not in seen:
            seen.append(topic)

    for token in tokenize(content):
        if token.startswith(("@", "http", "www")):
            continue
        token = token.strip("#")
        if len(token) < 3:
            continue
        if token not in seen:
            seen.append(token)
        if len(seen) >= max_topics:
            break

    for tag in tags or []:
        normalized = str(tag or "").lower().strip()
        if normalized and normalized not in seen:
            seen.append(normalized)

    return seen[:max_topics]


def extract_entities(text: str, author: str | None = None, max_entities: int = 8) -> list[str]:
    content = text or ""
    entities: list[str] = []

    for handle in _HANDLE_RE.findall(content):
        label = f"@{handle.lower()}"
        if label not in entities:
            entities.append(label)

    for match in _ENTITY_RE.findall(content):
        candidate = match.strip()
        if len(candidate) >= 3 and candidate not in entities:
            entities.append(candidate)
        if len(entities) >= max_entities:
            break

    if author:
        cleaned = str(author).strip()
        if cleaned and cleaned not in entities:
            entities.append(cleaned)

    return entities[:max_entities]


def semantic_group_for_item(item: dict[str, Any]) -> str:
    topics = item.get("related_topics") or []
    domain = infer_url_domain(item.get("canonical_url") or item.get("url"))
    platform = str(item.get("platform") or "unknown")
    if topics:
        return f"topic:{topics[0]}"
    if domain:
        return f"domain:{domain}"
    return f"platform:{platform}"


def cluster_id_for_item(item: dict[str, Any]) -> str:
    group = semantic_group_for_item(item)
    author = str(item.get("author_name") or item.get("author") or "")
    seed = f"{group}|{author[:80]}".encode("utf-8", errors="ignore")
    return hashlib.sha1(seed).hexdigest()[:16]


def infer_memory_relationships(
    conn,
    item: dict[str, Any],
    max_links: int = 12,
    similarity_threshold: float = 0.84,
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    text = build_semantic_text(item)
    if not text:
        return [], [], []

    domain = infer_url_domain(item.get("canonical_url") or item.get("url"))
    item_topics = extract_topics(text, tags=item.get("tags") or [])
    item_entities = extract_entities(text, author=item.get("author_name") or item.get("author"))
    item_vec = hash_embedding(text)

    cutoff = datetime.now(timezone.utc) - timedelta(days=365)
    where = ["id != ?", "captured_at >= ?", "archived_at IS NULL"]
    params: list[Any] = [str(item.get("id") or ""), cutoff.isoformat()]
    if domain:
        where.append("url_domain = ?")
        params.append(domain)
    query = f"""
        SELECT id, canonical_url, url_domain, text_content, image_captions, author_name, author, tags,
               related_topics, related_entities
        FROM items
        WHERE {" AND ".join(where)}
        ORDER BY captured_at DESC
        LIMIT 300
    """
    rows = conn.execute(query, params).fetchall()

    relations: list[dict[str, Any]] = []
    topic_counter: Counter[str] = Counter(item_topics)
    entity_counter: Counter[str] = Counter(item_entities)

    for row in rows:
        candidate = {
            "id": row["id"],
            "text_content": row["text_content"] or "",
            "image_captions": json.loads(row["image_captions"] or "[]"),
            "author_name": row["author_name"] if "author_name" in row.keys() else None,
            "author": row["author"],
            "tags": json.loads(row["tags"] or "[]") if "tags" in row.keys() and row["tags"] else [],
            "related_topics": json.loads(row["related_topics"] or "[]") if "related_topics" in row.keys() and row["related_topics"] else [],
            "related_entities": json.loads(row["related_entities"] or "[]") if "related_entities" in row.keys() and row["related_entities"] else [],
            "canonical_url": row["canonical_url"],
            "url_domain": row["url_domain"],
        }

        score = 0.0
        reasons: list[str] = []
        if domain and domain == str(candidate.get("url_domain") or ""):
            score += 0.25
            reasons.append("same_domain")

        candidate_text = build_semantic_text(candidate)
        if candidate_text:
            sim = cosine_similarity(item_vec, hash_embedding(candidate_text))
            if sim >= similarity_threshold:
                score += 0.5
                reasons.append(f"similar_embedding:{sim:.3f}")

        candidate_topics = set(candidate.get("related_topics") or extract_topics(candidate_text, candidate.get("tags") or []))
        candidate_entities = set(
            candidate.get("related_entities") or extract_entities(candidate_text, candidate.get("author_name") or candidate.get("author"))
        )
        shared_topics = set(item_topics).intersection(candidate_topics)
        shared_entities = set(item_entities).intersection(candidate_entities)

        if shared_topics:
            score += min(0.2, 0.06 * len(shared_topics))
            reasons.append("shared_topics")
            for topic in shared_topics:
                topic_counter[topic] += 1
        if shared_entities:
            score += min(0.2, 0.08 * len(shared_entities))
            reasons.append("shared_entities")
            for entity in shared_entities:
                entity_counter[entity] += 1

        if score <= 0.0:
            continue
        relations.append(
            {
                "to_id": str(candidate["id"]),
                "weight": round(score, 4),
                "reason": ",".join(reasons),
            }
        )

    relations.sort(key=lambda row: row["weight"], reverse=True)
    top_relations = relations[:max_links]
    top_topics = [topic for topic, _ in topic_counter.most_common(8)]
    top_entities = [entity for entity, _ in entity_counter.most_common(8)]
    return top_relations, top_topics, top_entities


def persist_relationships(conn, item_id: str, relations: list[dict[str, Any]]) -> None:
    conn.execute("DELETE FROM memory_links WHERE from_item_id = ?", (item_id,))
    now_iso = datetime.now(timezone.utc).isoformat()
    for rel in relations:
        conn.execute(
            """
            INSERT INTO memory_links(from_item_id, to_item_id, relation_type, weight, reason, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                item_id,
                rel["to_id"],
                "inferred",
                float(rel.get("weight", 0.0)),
                str(rel.get("reason") or ""),
                now_iso,
            ),
        )
