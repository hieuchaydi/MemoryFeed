from __future__ import annotations

from typing import Any

from backend.redaction import redact_value


def latest_capture_debug_payload(item: dict[str, Any] | None) -> dict[str, Any]:
    if not item:
        return {"ok": True, "item": None}
    payload = {
        "id": item.get("id"),
        "platform": item.get("platform"),
        "captured_at": item.get("captured_at"),
        "url": item.get("canonical_url") or item.get("url"),
        "selector_used": (item.get("capture_debug") or {}).get("selector_used", {}),
        "missing_fields": (item.get("capture_debug") or {}).get("missing_fields", []),
        "quality_flags": item.get("quality_flags", []),
        "capture_confidence": item.get("capture_confidence", 0.0),
        "confidence_reasons": item.get("confidence_reasons", []),
        "duplicate_reason": (item.get("capture_debug") or {}).get("duplicate_reason"),
        "capture_method": item.get("capture_method"),
        "extractor_version": item.get("extractor_version"),
        "capture_source": item.get("capture_source"),
        "replay_source": item.get("replay_source"),
        "suspicious_prompt_content": bool(item.get("suspicious_prompt_content", False)),
    }
    return {"ok": True, "item": redact_value(payload)}
