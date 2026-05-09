from __future__ import annotations

import json
import os
from dataclasses import dataclass

VALID_AI_PROVIDERS = {"none", "gemini", "groq", "auto"}
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1", "testclient"}


@dataclass(frozen=True)
class RuntimeConfig:
    offline_only: bool
    ai_provider: str
    public_mode: bool
    admin_token: str
    mcp_max_results: int
    mcp_allow_timeline: bool
    mcp_allow_active_feed: bool
    mcp_redact_output: bool
    memory_semantic_dedupe: bool
    memory_dedupe_similarity_threshold: float
    memory_dedupe_window_hours: int
    memory_platform_dedupe_windows: dict[str, int]
    memory_sanitize_prompt_content: bool
    memory_skip_sensitive_embedding: bool
    memory_retention_days: int
    memory_auto_archive: bool
    memory_archive_low_score_threshold: float


def env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int, min_value: int = 1, max_value: int | None = None) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        parsed = int(raw)
    except ValueError:
        parsed = default
    if parsed < min_value:
        parsed = min_value
    if max_value is not None and parsed > max_value:
        parsed = max_value
    return parsed


def env_float(name: str, default: float, min_value: float = 0.0, max_value: float | None = None) -> float:
    raw = os.getenv(name, str(default)).strip()
    try:
        parsed = float(raw)
    except ValueError:
        parsed = default
    if parsed < min_value:
        parsed = min_value
    if max_value is not None and parsed > max_value:
        parsed = max_value
    return parsed


def env_json_int_map(
    name: str,
    *,
    min_value: int = 1,
    max_value: int = 24 * 30,
) -> dict[str, int]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except Exception:
        return {}
    if not isinstance(parsed, dict):
        return {}
    out: dict[str, int] = {}
    for key, value in parsed.items():
        if not isinstance(key, str):
            continue
        try:
            hours = int(value)
        except Exception:
            continue
        hours = max(min_value, min(max_value, hours))
        out[key.strip().lower()] = hours
    return out


def load_runtime_config() -> RuntimeConfig:
    offline_only = env_flag("OFFLINE_ONLY", default=False)
    ai_provider = (os.getenv("MEMORYFEED_AI_PROVIDER", "auto").strip().lower() or "auto")
    if ai_provider not in VALID_AI_PROVIDERS:
        ai_provider = "auto"
    if offline_only:
        ai_provider = "none"

    return RuntimeConfig(
        offline_only=offline_only,
        ai_provider=ai_provider,
        public_mode=env_flag("MEMORYFEED_PUBLIC_MODE", default=False),
        admin_token=os.getenv("MEMORYFEED_ADMIN_TOKEN", "").strip(),
        mcp_max_results=env_int("MEMORYFEED_MCP_MAX_RESULTS", default=5, min_value=1, max_value=50),
        mcp_allow_timeline=env_flag("MEMORYFEED_MCP_ALLOW_TIMELINE", default=False),
        mcp_allow_active_feed=env_flag("MEMORYFEED_MCP_ALLOW_ACTIVE_FEED", default=True),
        mcp_redact_output=env_flag("MEMORYFEED_MCP_REDACT_OUTPUT", default=True),
        memory_semantic_dedupe=env_flag("MEMORY_SEMANTIC_DEDUPE", default=True),
        memory_dedupe_similarity_threshold=env_float(
            "MEMORY_DEDUPE_SIMILARITY_THRESHOLD",
            default=0.92,
            min_value=0.5,
            max_value=0.999,
        ),
        memory_dedupe_window_hours=env_int("MEMORY_DEDUPE_WINDOW_HOURS", default=2, min_value=1, max_value=24 * 30),
        memory_platform_dedupe_windows=env_json_int_map("MEMORY_PLATFORM_DEDUPE_WINDOWS"),
        memory_sanitize_prompt_content=env_flag("MEMORY_SANITIZE_PROMPT_CONTENT", default=True),
        memory_skip_sensitive_embedding=env_flag("MEMORY_SKIP_SENSITIVE_EMBEDDING", default=True),
        memory_retention_days=env_int("MEMORY_RETENTION_DAYS", default=365, min_value=7, max_value=36500),
        memory_auto_archive=env_flag("MEMORY_AUTO_ARCHIVE", default=True),
        memory_archive_low_score_threshold=env_float(
            "MEMORY_ARCHIVE_LOW_SCORE_THRESHOLD",
            default=0.35,
            min_value=0.0,
            max_value=1.0,
        ),
    )


def provider_enabled(provider: str, config: RuntimeConfig | None = None) -> bool:
    cfg = config or load_runtime_config()
    name = provider.strip().lower()
    if name not in {"gemini", "groq"}:
        return False
    if cfg.offline_only or cfg.ai_provider == "none":
        return False
    if cfg.ai_provider == "auto":
        return True
    return cfg.ai_provider == name


def provider_requires_key(provider: str, config: RuntimeConfig | None = None) -> bool:
    cfg = config or load_runtime_config()
    name = provider.strip().lower()
    if cfg.offline_only or cfg.ai_provider == "none":
        return False
    if cfg.ai_provider == "auto":
        return False
    return cfg.ai_provider == name


def is_public_bind_host(host: str) -> bool:
    return host.strip().lower() not in LOOPBACK_HOSTS


def is_localhost_client(client_host: str | None) -> bool:
    if not client_host:
        return False
    normalized = client_host.split(",", 1)[0].strip().lower()
    return normalized in LOOPBACK_HOSTS


def dedupe_window_hours_for_platform(platform: str | None, config: RuntimeConfig | None = None) -> int:
    cfg = config or load_runtime_config()
    key = (platform or "").strip().lower()
    if key and key in cfg.memory_platform_dedupe_windows:
        return int(cfg.memory_platform_dedupe_windows[key])
    return int(cfg.memory_dedupe_window_hours)
