from __future__ import annotations

import io
import os
from dataclasses import dataclass
from typing import Any

import httpx
from PIL import Image

GEMINI_MODEL = os.getenv("MEMORYFEED_GEMINI_MODEL", "gemini-2.5-flash")
GROQ_MODEL = os.getenv("MEMORYFEED_GROQ_MODEL", "qwen/qwen3-32b")


@dataclass
class ProviderState:
    provider: str
    enabled: bool
    reason: str
    model: str


def gemini_api_key() -> str:
    return os.getenv("GEMINI_API_KEY", "").strip()


def groq_api_key() -> str:
    return os.getenv("GROQ_API_KEY", "").strip()


def gemini_state() -> ProviderState:
    if not gemini_api_key():
        return ProviderState("gemini", False, "Missing GEMINI_API_KEY", GEMINI_MODEL)
    return ProviderState("gemini", True, "configured", GEMINI_MODEL)


def groq_state() -> ProviderState:
    if not groq_api_key():
        return ProviderState("groq", False, "Missing GROQ_API_KEY", GROQ_MODEL)
    return ProviderState("groq", True, "configured", GROQ_MODEL)


def caption_image_with_gemini(image_bytes: bytes, prompt: str) -> str:
    key = gemini_api_key()
    if not key:
        return ""
    try:
        from google import genai
    except Exception:
        return ""

    try:
        client = genai.Client(api_key=key)
        image = Image.open(io.BytesIO(image_bytes))
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[prompt, image],
        )
        text = getattr(response, "text", None)
        if isinstance(text, str) and text.strip():
            return text.strip()
        return _extract_gemini_text(response)
    except Exception:
        return ""


def rewrite_or_summarize_with_groq(user_text: str) -> str:
    key = groq_api_key()
    if not key or not user_text.strip():
        return ""
    try:
        from groq import Groq
    except Exception:
        return ""

    try:
        client = Groq(api_key=key)
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Bạn là trợ lý tóm tắt ngắn gọn. Hãy viết lại nội dung mạng xã hội nhiều nhiễu "
                        "thành đoạn tóm tắt súc tích, dễ tìm kiếm, nêu rõ thực thể chính và ý định. "
                        "Giữ nguyên ngôn ngữ gốc của nội dung."
                    ),
                },
                {"role": "user", "content": user_text[:4000]},
            ],
            temperature=0.1,
        )
        content = completion.choices[0].message.content
        return str(content).strip() if content else ""
    except Exception:
        return ""


def check_gemini_connectivity(timeout_s: float = 8.0) -> tuple[bool, str]:
    key = gemini_api_key()
    if not key:
        return False, "Missing GEMINI_API_KEY"
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
    try:
        resp = httpx.get(url, timeout=timeout_s)
        if resp.status_code == 200:
            return True, "ok"
        return False, f"HTTP {resp.status_code}"
    except Exception as exc:
        return False, str(exc)


def check_groq_connectivity(timeout_s: float = 8.0) -> tuple[bool, str]:
    key = groq_api_key()
    if not key:
        return False, "Missing GROQ_API_KEY"
    try:
        resp = httpx.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {key}"},
            timeout=timeout_s,
        )
        if resp.status_code == 200:
            return True, "ok"
        return False, f"HTTP {resp.status_code}"
    except Exception as exc:
        return False, str(exc)


def providers_snapshot() -> dict[str, Any]:
    gs = gemini_state()
    qs = groq_state()
    return {
        "gemini": {"enabled": gs.enabled, "reason": gs.reason, "model": gs.model},
        "groq": {"enabled": qs.enabled, "reason": qs.reason, "model": qs.model},
    }


def _extract_gemini_text(response: Any) -> str:
    try:
        candidates = getattr(response, "candidates", None) or []
        out: list[str] = []
        for cand in candidates:
            content = getattr(cand, "content", None)
            parts = getattr(content, "parts", None) if content is not None else None
            if not parts:
                continue
            for part in parts:
                text = getattr(part, "text", None)
                if isinstance(text, str) and text.strip():
                    out.append(text.strip())
        return "\n".join(out).strip()
    except Exception:
        return ""
