from __future__ import annotations

import hashlib
import re

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_#@-]{2,}")
_ENTITY_RE = re.compile(r"(@[A-Za-z0-9_]+|#[A-Za-z0-9_]+|\b[A-Z]{2,}\b)")
_STOPWORDS = {
    "this",
    "that",
    "with",
    "from",
    "have",
    "will",
    "about",
    "there",
    "would",
    "could",
    "should",
    "their",
    "because",
    "while",
    "where",
}


def derive_graph_fields(item: dict) -> dict[str, object]:
    text = str(item.get("text_content") or "")
    words = [w.lower() for w in _WORD_RE.findall(text)]
    topics: list[str] = []
    seen = set()
    for w in words:
        if len(w) < 4 or w in _STOPWORDS:
            continue
        if w not in seen:
            topics.append(w)
            seen.add(w)
        if len(topics) >= 8:
            break

    entities = []
    seen_e = set()
    for match in _ENTITY_RE.findall(text):
        token = match.strip()
        if token and token not in seen_e:
            entities.append(token)
            seen_e.add(token)
        if len(entities) >= 8:
            break

    group_seed = "|".join(topics[:3] + entities[:2]).encode("utf-8", errors="ignore")
    semantic_group = hashlib.sha1(group_seed).hexdigest()[:12] if group_seed else None
    return {
        "related_topics": topics,
        "related_entities": entities,
        "semantic_group": semantic_group,
    }
