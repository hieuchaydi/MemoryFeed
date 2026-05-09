from __future__ import annotations


def explain_duplicate_decision(item: dict) -> str:
    key = str(item.get("dedupe_key") or "")[:12]
    canonical = str(item.get("canonical_url") or item.get("url") or "")
    return f"duplicate fingerprint matched dedupe_key={key} canonical={canonical}"


def explain_ranking_penalties(factors: dict[str, float]) -> dict[str, float]:
    return {
        "duplicate_penalty": float(factors.get("duplicate_penalty") or 0.0),
        "confidence_penalty": float(factors.get("confidence_penalty") or 0.0),
        "noise_penalty": float(factors.get("noise_penalty") or 0.0),
    }


def explain_archival_decision(item: dict) -> str:
    state = str(item.get("aging_state") or "active")
    decay = float(item.get("decay_score") or 0.0)
    return f"aging_state={state} decay_score={decay:.3f}"


def explain_confidence_reduction(item: dict) -> str:
    flags = item.get("quality_flags") or []
    missing = [f for f in flags if str(f).startswith("missing_")]
    return "no_reduction" if not missing else f"missing_fields={','.join(missing[:5])}"
