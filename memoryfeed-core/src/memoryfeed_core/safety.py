from __future__ import annotations

import base64
import re

_PROMPT_PATTERNS: list[tuple[re.Pattern[str], str, float]] = [
    (re.compile(r"\bignore\s+(all|previous)\s+instructions\b", re.IGNORECASE), "ignore_previous_instructions", 0.45),
    (re.compile(r"\bsystem\s+prompt\b", re.IGNORECASE), "system_prompt_manipulation", 0.25),
    (re.compile(r"\bdeveloper\s+message\b", re.IGNORECASE), "developer_message_manipulation", 0.25),
    (re.compile(r"\bjailbreak\b", re.IGNORECASE), "jailbreak_pattern", 0.35),
    (re.compile(r"<\|.*?\|>"), "token_roleplay_sequence", 0.25),
    (re.compile(r"\b(roleplay|act as)\s+(system|assistant)\b", re.IGNORECASE), "roleplay_override", 0.3),
]

_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE_RE = re.compile(r"(?<!\w)\+?\d[\d\s().-]{8,}\d\b")
_TOKEN_RE = re.compile(r"\b(?:Bearer|token)\s+[A-Za-z0-9._\-+/=]{16,}\b", re.IGNORECASE)
_PASS_RE = re.compile(r"\b(password|passwd|pwd)\s*[:=]\s*\S+", re.IGNORECASE)
_KEY_RE = re.compile(r"\b(?:sk|rk|pk|api|key)[_-]?[A-Za-z0-9]{16,}\b", re.IGNORECASE)
_INVITE_RE = re.compile(r"(discord\.gg/|slack\.com/invite/|t\.me/\+)", re.IGNORECASE)
_AUTH_URL_RE = re.compile(r"https?://\S+(token|session|auth)=\S+", re.IGNORECASE)


def assess_prompt_risk(text: str) -> tuple[float, str | None]:
    data = str(text or "")
    score = 0.0
    reasons: list[str] = []
    for pattern, reason, weight in _PROMPT_PATTERNS:
        if pattern.search(data):
            score += weight
            reasons.append(reason)
    for token in data.split():
        if len(token) >= 24 and _looks_like_base64(token):
            score += 0.15
            reasons.append("encoded_prompt_like_payload")
            break
    score = max(0.0, min(1.0, score))
    return round(score, 6), (reasons[0] if reasons else None)


def classify_sensitivity(text: str, url: str = "") -> tuple[str, list[str]]:
    combined = f"{text}\n{url}"
    reasons: list[str] = []
    if _KEY_RE.search(combined):
        reasons.append("api_key")
    if _TOKEN_RE.search(combined):
        reasons.append("token")
    if _PASS_RE.search(combined):
        reasons.append("password")
    if _INVITE_RE.search(combined):
        reasons.append("invite_link")
    if _EMAIL_RE.search(combined):
        reasons.append("personal_email")
    if _PHONE_RE.search(combined):
        reasons.append("phone_number")
    if _AUTH_URL_RE.search(combined):
        reasons.append("auth_session_url")

    if not reasons:
        return "none", []
    if any(r in {"api_key", "token", "password", "auth_session_url"} for r in reasons):
        return "high", reasons
    if len(reasons) >= 2:
        return "medium", reasons
    return "low", reasons


def _looks_like_base64(token: str) -> bool:
    cleaned = token.strip().strip("'\"")
    if len(cleaned) % 4 != 0:
        return False
    if not re.fullmatch(r"[A-Za-z0-9+/=]+", cleaned):
        return False
    try:
        base64.b64decode(cleaned, validate=True)
    except Exception:
        return False
    return True


def detect_prompt_injection(text: str) -> dict[str, object]:
    data = str(text or "")
    signals: list[str] = []
    if re.search(r"\bignore\s+(all|previous)\s+instructions\b", data, re.IGNORECASE):
        signals.append("ignore_previous_instructions")
    if re.search(r"\breveal\s+(secrets?|credentials?)\b", data, re.IGNORECASE):
        signals.append("reveal_secrets")
    if re.search(r"\bsystem\s+prompt\b", data, re.IGNORECASE):
        signals.append("system_prompt_manipulation")
    score, _ = assess_prompt_risk(data)
    return {"suspicious": bool(signals) or score >= 0.4, "signals": signals}


def sanitize_untrusted_text(text: str) -> str:
    out = str(text or "")
    out = re.sub(r"\bignore\s+(all|previous)\s+instructions\b", "[SANITIZED_INSTRUCTION]", out, flags=re.IGNORECASE)
    out = re.sub(r"\breveal\s+(secrets?|credentials?)\b", "[SANITIZED_SECRET_REQUEST]", out, flags=re.IGNORECASE)
    return out


def sanitize_untrusted_payload(value: object) -> object:
    if isinstance(value, str):
        return sanitize_untrusted_text(value)
    if isinstance(value, dict):
        return {k: sanitize_untrusted_payload(v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize_untrusted_payload(v) for v in value]
    return value
