from __future__ import annotations

import hashlib
import re
from urllib.parse import urlparse


_WORD_RE = re.compile(r"[a-z0-9]{3,}")


def near_duplicate_cluster_key(item: dict) -> str:
    canonical = str(item.get("canonical_url") or item.get("url") or "").strip().lower()
    if canonical:
        try:
            parsed = urlparse(canonical)
            host = parsed.netloc
            path = parsed.path.rstrip("/")
            return f"url:{host}{path}"
        except Exception:
            return f"url:{canonical}"
    text = str(item.get("text_content") or "").lower()
    words = _WORD_RE.findall(text)[:16]
    seed = " ".join(words).encode("utf-8", errors="ignore")
    return "txt:" + hashlib.sha1(seed).hexdigest()


def diversity_rerank(
    rows: list[dict],
    factor: float = 0.3,
) -> list[dict]:
    if factor <= 0.0 or len(rows) < 3:
        return rows
    out: list[dict] = []
    seen_clusters: dict[str, int] = {}
    seen_platforms: dict[str, int] = {}
    for row in rows:
        cluster = near_duplicate_cluster_key(row)
        platform = str(row.get("platform") or "unknown").lower()
        dup_count = seen_clusters.get(cluster, 0)
        platform_count = seen_platforms.get(platform, 0)
        diversity_penalty = (dup_count * factor) + (platform_count * (factor * 0.35))
        adjusted = dict(row)
        adjusted["diversity_penalty"] = round(diversity_penalty, 6)
        adjusted["score"] = round(float(row.get("score") or 0.0) - diversity_penalty, 8)
        out.append(adjusted)
        seen_clusters[cluster] = dup_count + 1
        seen_platforms[platform] = platform_count + 1
    out.sort(key=lambda item: float(item.get("score") or 0.0), reverse=True)
    return out
