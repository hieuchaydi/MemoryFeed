from __future__ import annotations

import re
from typing import Any

from backend.safety import classify_sensitivity as detect_sensitivity

_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE_RE = re.compile(r"(?<!\w)\+?\d[\d\s().-]{8,}\d\b")
_BEARER_RE = re.compile(r"\bBearer\s+[A-Za-z0-9._\-+/=]{16,}\b", re.IGNORECASE)
_API_KEY_RE = re.compile(r"\b(?:sk|rk|pk|api|key)[_-]?[A-Za-z0-9]{16,}\b", re.IGNORECASE)


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


def classify_sensitivity(text: str, url: str = "") -> tuple[str, list[str]]:
    return detect_sensitivity(text=text, url=url)
