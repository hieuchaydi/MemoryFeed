from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from backend.redaction import redact_value

_ALLOWED_FIELDS = {
    "event_type",
    "platform",
    "selector_used",
    "quality_flags",
    "duplicate_reason",
    "embedding_skipped_reason",
    "suspicious_prompt_content",
    "benchmark_context",
    "item_id",
    "status",
    "count",
    "version",
}


def log_event(logger: logging.Logger, event_type: str, **fields: Any) -> None:
    payload: dict[str, Any] = {
        "event_type": event_type,
        "time": datetime.now(timezone.utc).isoformat(),
    }
    for key, value in fields.items():
        if key in _ALLOWED_FIELDS:
            payload[key] = value
    safe_payload = redact_value(payload)
    logger.info(json.dumps(safe_payload, ensure_ascii=False))
