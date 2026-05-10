from __future__ import annotations

import hashlib
import math
import re
from typing import Any

_TOKEN_RE = re.compile(r"[A-Za-z0-9_@#][A-Za-z0-9_@#\-/.:]{1,40}")
_STOPWORDS = {
    "the",
    "and",
    "for",
    "that",
    "with",
    "this",
    "from",
    "your",
    "you",
    "are",
    "was",
    "were",
    "have",
    "has",
    "had",
    "will",
    "can",
    "not",
    "but",
    "about",
    "into",
    "https",
    "http",
    "www",
    "com",
}


def build_semantic_text(item: dict[str, Any]) -> str:
    text = str(item.get("text_content") or "").strip()
    captions = " ".join(item.get("image_captions") or []).strip()
    tags = " ".join(item.get("tags") or []).strip()
    author = str(item.get("author_name") or item.get("author") or "").strip()
    merged = " \n ".join(part for part in [text, captions, tags, author] if part)
    if not merged:
        return ""
    words = merged.split()
    if len(words) > 512:
        words = words[:512]
    return " ".join(words)


def tokenize(text: str) -> list[str]:
    values = [m.group(0).lower() for m in _TOKEN_RE.finditer(text or "")]
    return [token for token in values if token not in _STOPWORDS]


def hash_embedding(text: str, dimensions: int = 128) -> list[float]:
    dims = max(16, int(dimensions))
    if not text.strip():
        return [0.0] * dims

    vec = [0.0] * dims
    for token in tokenize(text):
        digest = hashlib.sha256(token.encode("utf-8", errors="ignore")).digest()
        idx = int.from_bytes(digest[:2], byteorder="big") % dims
        sign = 1.0 if (digest[2] % 2 == 0) else -1.0
        weight = 1.0 + (digest[3] / 255.0) * 0.2
        vec[idx] += sign * weight

    return normalize(vec)


def normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vector))
    if norm <= 1e-9:
        return [0.0 for _ in vector]
    return [x / norm for x in vector]


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    if not vec_a or not vec_b:
        return 0.0
    n = min(len(vec_a), len(vec_b))
    if n == 0:
        return 0.0
    return float(sum(vec_a[i] * vec_b[i] for i in range(n)))
