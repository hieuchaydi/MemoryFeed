from __future__ import annotations

import os
from dataclasses import dataclass

VALID_AI_PROVIDERS = {"none", "gemini", "groq", "auto"}
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


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
    search_diversity: bool
    search_diversity_factor: float
    enable_decay: bool
    decay_half_life_days: int
    hide_sensitive_from_search: bool
    skip_sensitive_embedding: bool
    background_maintenance: bool
    maintenance_interval_seconds: int


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


def env_float(name: str, default: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    raw = os.getenv(name, str(default)).strip()
    try:
        parsed = float(raw)
    except ValueError:
        parsed = default
    if parsed < min_value:
        parsed = min_value
    if parsed > max_value:
        parsed = max_value
    return parsed


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
        search_diversity=env_flag("MEMORY_SEARCH_DIVERSITY", default=True),
        search_diversity_factor=env_float("MEMORY_SEARCH_DIVERSITY_FACTOR", default=0.3, min_value=0.0, max_value=1.0),
        enable_decay=env_flag("MEMORY_ENABLE_DECAY", default=True),
        decay_half_life_days=env_int("MEMORY_DECAY_HALF_LIFE_DAYS", default=90, min_value=7, max_value=3650),
        hide_sensitive_from_search=env_flag("MEMORY_HIDE_SENSITIVE_FROM_SEARCH", default=True),
        skip_sensitive_embedding=env_flag("MEMORY_SKIP_SENSITIVE_EMBEDDING", default=True),
        background_maintenance=env_flag("MEMORY_BACKGROUND_MAINTENANCE", default=True),
        maintenance_interval_seconds=env_int("MEMORY_MAINTENANCE_INTERVAL_SECONDS", default=600, min_value=60, max_value=86400),
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
