from __future__ import annotations

import re
from typing import Any

_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE_RE = re.compile(r"(?<!\w)\+?\d[\d\s().-]{8,}\d\b")
_BEARER_RE = re.compile(r"\bBearer\s+[A-Za-z0-9._\-+/=]{16,}\b", re.IGNORECASE)
_API_KEY_RE = re.compile(r"\b(?:sk|rk|pk|api|key)[_-]?[A-Za-z0-9]{16,}\b", re.IGNORECASE)
_OPENAI_KEY_RE = re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")
_AWS_KEY_RE = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")
_GENERIC_SECRET_RE = re.compile(r"\b(?:secret|token|passwd|password|apikey|api_key)\s*[:=]\s*[^\s]{8,}\b", re.IGNORECASE)
_INVITE_LINK_RE = re.compile(r"\bhttps?://(?:discord\.gg|chat\.whatsapp\.com|t\.me/joinchat|slack\.com/invite)/[^\s]+", re.IGNORECASE)


def redact_text(value: str) -> str:
    out = _EMAIL_RE.sub("[REDACTED_EMAIL]", value)
    out = _PHONE_RE.sub("[REDACTED_PHONE]", out)
    out = _BEARER_RE.sub("Bearer [REDACTED_TOKEN]", out)
    out = _API_KEY_RE.sub("[REDACTED_KEY]", out)
    return out


def redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, dict):
        return {key: redact_value(item) for key, item in value.items()}
    return value


def scan_sensitive_content(value: str) -> dict[str, Any]:
    text = value or ""
    reasons: list[str] = []
    if _EMAIL_RE.search(text):
        reasons.append("email")
    if _BEARER_RE.search(text):
        reasons.append("bearer_token")
    if _OPENAI_KEY_RE.search(text) or _API_KEY_RE.search(text):
        reasons.append("api_key")
    if _AWS_KEY_RE.search(text):
        reasons.append("aws_access_key")
    if _JWT_RE.search(text):
        reasons.append("jwt_token")
    if _INVITE_LINK_RE.search(text):
        reasons.append("invite_link")
    if _GENERIC_SECRET_RE.search(text):
        reasons.append("secret_like_string")
    return {
        "sensitive": bool(reasons),
        "reasons": sorted(set(reasons)),
    }
