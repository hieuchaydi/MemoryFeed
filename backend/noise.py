from __future__ import annotations

import re

_ENGAGEMENT_BAIT_RE = re.compile(
    r"\b(like\s+and\s+subscribe|follow\s+for\s+more|comment\s+below|tag\s+\d+\s+friends)\b",
    re.IGNORECASE,
)
_SPAM_RE = re.compile(r"(free\s+money|crypto\s+giveaway|airdrop|dm\s+me\s+now)", re.IGNORECASE)
_REPOST_RE = re.compile(r"\b(repost|retweet|shared\s+from|via\s+@)\b", re.IGNORECASE)
_MEME_RE = re.compile(r"\b(meme|template|reaction|shitpost)\b", re.IGNORECASE)


def classify_noise(item: dict) -> tuple[float, str | None]:
    text = str(item.get("text_content") or "")
    lower = text.lower()
    reasons: list[str] = []
    score = 0.0

    if len(lower.strip()) < 18:
        score += 0.35
        reasons.append("low_information_content")
    if _ENGAGEMENT_BAIT_RE.search(lower):
        score += 0.25
        reasons.append("engagement_bait")
    if _SPAM_RE.search(lower):
        score += 0.35
        reasons.append("spam_like_content")
    if _REPOST_RE.search(lower):
        score += 0.2
        reasons.append("repetitive_repost")
    if _MEME_RE.search(lower) and len(lower) < 120:
        score += 0.18
        reasons.append("duplicate_meme_variant")

    media_urls = item.get("media_urls") or item.get("image_urls") or []
    if isinstance(media_urls, list) and len(media_urls) > 3:
        score += 0.1
        reasons.append("high_link_density")

    final = max(0.0, min(1.0, score))
    return final, reasons[0] if reasons else None
