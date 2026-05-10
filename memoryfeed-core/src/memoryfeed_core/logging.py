from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from memoryfeed_core.redaction import redact_value

_ALLOWED_FIELDS = {
    "event_type",
    "platform",
    "selector_used",
    "quality_flags",
    "duplicate_reason",
    "embedding_skipped_reason",
    "suspicious_prompt_content",
    "benchmark_context",
    "capture_confidence",
    "confidence_reasons",
    "item_id",
    "status",
    "count",
    "version",
}

_SENSITIVE_QUERY_KEYS = {"token", "key", "session", "auth", "bearer", "apikey", "api_key"}
_MAX_STRING = 512
_MAX_LIST = 30


def _strip_sensitive_query_from_url(value: str) -> str:
    text = value.strip()
    if "://" not in text or "?" not in text:
        return text
    try:
        parsed = urlparse(text)
        clean_items = []
        for key, raw_val in parse_qsl(parsed.query, keep_blank_values=True):
            lower_key = key.lower()
            if lower_key in _SENSITIVE_QUERY_KEYS:
                continue
            clean_items.append((key, raw_val))
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, urlencode(clean_items, doseq=True), ""))
    except Exception:
        return text


def _sanitize_for_log(value: Any) -> Any:
    if isinstance(value, str):
        stripped = _strip_sensitive_query_from_url(value)
        if len(stripped) > _MAX_STRING:
            return stripped[:_MAX_STRING] + "...[truncated]"
        return stripped
    if isinstance(value, list):
        return [_sanitize_for_log(item) for item in value[:_MAX_LIST]]
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for idx, (key, item) in enumerate(value.items()):
            if idx >= 80:
                break
            out[str(key)] = _sanitize_for_log(item)
        return out
    return value


def log_event(logger: logging.Logger, event_type: str, **fields: Any) -> None:
    payload: dict[str, Any] = {
        "event_type": event_type,
        "time": datetime.now(timezone.utc).isoformat(),
    }
    for key, value in fields.items():
        if key in _ALLOWED_FIELDS:
            payload[key] = value
    safe_payload = _sanitize_for_log(redact_value(payload))
    logger.info(json.dumps(safe_payload, ensure_ascii=False))

