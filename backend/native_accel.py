from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass
class NativeStatus:
    enabled: bool
    reason: str


try:
    import memoryfeed_native as _native

    STATUS = NativeStatus(enabled=True, reason="memoryfeed_native loaded")
except Exception as exc:  # pragma: no cover
    _native = None
    STATUS = NativeStatus(enabled=False, reason=str(exc))


def is_enabled() -> bool:
    return STATUS.enabled


def status() -> dict[str, str | bool]:
    return {"enabled": STATUS.enabled, "reason": STATUS.reason}


def normalize_text_fast(text: str, max_len: int = 2000) -> str:
    if _native is not None:
        try:
            return _native.normalize_text(text, max_len)
        except Exception:
            pass

    compact = " ".join((text or "").split())
    return compact[:max_len]


def rrf_fuse_fast(fts_ids: list[str], semantic_ids: list[str], k: int = 60) -> dict[str, float]:
    if _native is not None:
        try:
            return _native.rrf_fuse(fts_ids, semantic_ids, int(k))
        except Exception:
            pass

    rank_fts = {item_id: idx + 1 for idx, item_id in enumerate(fts_ids)}
    rank_sem = {item_id: idx + 1 for idx, item_id in enumerate(semantic_ids)}

    out: dict[str, float] = {}
    for item_id in dict.fromkeys([*fts_ids, *semantic_ids]):
        score = 0.0
        if item_id in rank_fts:
            score += 1.0 / (rank_fts[item_id] + k)
        if item_id in rank_sem:
            score += 1.0 / (rank_sem[item_id] + k)
        out[item_id] = score
    return out
