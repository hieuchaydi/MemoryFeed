from __future__ import annotations

import os
from dataclasses import dataclass

from backend.runtime_config import RuntimeConfig


@dataclass(frozen=True)
class PrivacyGuardReport:
    local_only_verified: bool
    violations: list[str]


def verify_local_only_mode(cfg: RuntimeConfig) -> PrivacyGuardReport:
    violations: list[str] = []
    if cfg.offline_only and cfg.ai_provider != "none":
        violations.append("offline_only_requires_ai_provider_none")
    if cfg.offline_only:
        if os.getenv("GEMINI_API_KEY", "").strip():
            violations.append("gemini_key_present_in_offline_mode")
        if os.getenv("GROQ_API_KEY", "").strip():
            violations.append("groq_key_present_in_offline_mode")
    return PrivacyGuardReport(local_only_verified=len(violations) == 0, violations=violations)
