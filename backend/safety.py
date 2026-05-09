from __future__ import annotations

import re
from typing import Any

_PROMPT_INJECTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("ignore_previous_instructions", re.compile(r"\bignore\s+(all\s+)?(previous|prior)\s+instructions\b", re.IGNORECASE)),
    ("reveal_secrets", re.compile(r"\b(reveal|exfiltrate|leak)\s+(all\s+)?(secrets?|tokens?|credentials?)\b", re.IGNORECASE)),
    ("send_tokens", re.compile(r"\b(send|share|dump)\s+(api\s+)?tokens?\b", re.IGNORECASE)),
    ("system_prompt", re.compile(r"\bsystem\s+prompt\b", re.IGNORECASE)),
    ("jailbreak", re.compile(r"\b(jailbreak|developer\s+mode|dan\s+mode|bypass\s+safety)\b", re.IGNORECASE)),
    ("tool_abuse", re.compile(r"\b(run|execute)\s+(shell|terminal|command)\b", re.IGNORECASE)),
)


def detect_prompt_injection(text: str) -> dict[str, Any]:
    haystack = text or ""
    hits: list[str] = []
    for label, pattern in _PROMPT_INJECTION_PATTERNS:
        if pattern.search(haystack):
            hits.append(label)
    return {
        "suspicious": bool(hits),
        "signals": hits,
    }


def sanitize_untrusted_text(text: str) -> str:
    if not text:
        return text
    out = text
    out = re.sub(r"(?i)\b(ignore\s+(all\s+)?(previous|prior)\s+instructions)\b", "[SANITIZED_INSTRUCTION]", out)
    out = re.sub(r"(?i)\b(system\s+prompt)\b", "[SANITIZED_SYSTEM_PROMPT_REF]", out)
    out = re.sub(
        r"(?i)\b(reveal|exfiltrate|leak|dump|send|share)\s+(all\s+)?(secrets?|tokens?|credentials?)\b",
        "[SANITIZED_SECRET_REQUEST]",
        out,
    )
    return out


def sanitize_untrusted_payload(value: Any) -> Any:
    if isinstance(value, str):
        return sanitize_untrusted_text(value)
    if isinstance(value, list):
        return [sanitize_untrusted_payload(x) for x in value]
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if lowered in {"text_content", "text_excerpt", "note"}:
                sanitized[key] = sanitize_untrusted_text(str(item or ""))
            else:
                sanitized[key] = sanitize_untrusted_payload(item)
        return sanitized
    return value
