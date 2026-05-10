from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

TRACKING_QUERY_KEYS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "utm_id",
    "gclid",
    "fbclid",
    "igshid",
    "mc_cid",
    "mc_eid",
    "spm",
    "ref",
    "ref_src",
}

SENSITIVE_OR_SESSION_KEYS = {
    "session",
    "sessionid",
    "sid",
    "phpsessid",
    "jsessionid",
    "token",
    "auth",
    "authorization",
    "bearer",
    "api_key",
    "apikey",
    "key",
}

YOUTUBE_MEANINGFUL_QUERY = {
    "v",
    "t",
    "start",
    "time_continue",
    "list",
    "index",
}

FACEBOOK_MEANINGFUL_QUERY = {
    "story_fbid",
    "id",
    "comment_id",
    "reply_comment_id",
}

MEDIA_INDEX_KEYS = {"index", "i", "img_index"}


def _normalized_host(host: str) -> str:
    value = (host or "").strip().lower()
    if value.startswith("www."):
        value = value[4:]
    return value


def _clean_path(path: str) -> str:
    out = path or "/"
    if out != "/" and out.endswith("/"):
        out = out.rstrip("/")
    return out or "/"


def _is_tracking_or_sensitive_key(key: str) -> bool:
    k = key.lower().strip()
    if not k:
        return True
    if k in TRACKING_QUERY_KEYS or k in SENSITIVE_OR_SESSION_KEYS:
        return True
    return False


def _extract_timestamp_from_hash(fragment: str) -> str | None:
    value = (fragment or "").lstrip("#")
    if not value:
        return None
    # Supports fragments like #t=1m30s or #1m30s
    if value.startswith("t="):
        return value[2:]
    if re.fullmatch(r"\d+[smh]?\d*[sm]?", value):
        return value
    return None


def _clean_query_items(items: list[tuple[str, str]]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for key, value in items:
        clean_key = (key or "").strip()
        clean_val = (value or "").strip()
        if not clean_key or _is_tracking_or_sensitive_key(clean_key):
            continue
        out.append((clean_key, clean_val))
    return out


def canonicalize_url(url: str, platform: str = "unknown") -> str:
    raw = (url or "").strip()
    if not raw:
        return ""
    try:
        parsed = urlparse(raw)
    except Exception:
        return raw

    scheme = parsed.scheme or "https"
    host = _normalized_host(parsed.netloc)
    path = _clean_path(parsed.path)
    platform_name = (platform or "unknown").strip().lower()
    query_items = parse_qsl(parsed.query, keep_blank_values=False)
    query_items = _clean_query_items(query_items)
    fragment = ""

    if platform_name == "twitter":
        match = re.search(r"/([^/]+)/status/(\d+)", path)
        if match:
            path = f"/{match.group(1)}/status/{match.group(2)}"
        query_items = []
    elif platform_name == "youtube":
        if host == "youtu.be":
            extras = {k: v for k, v in query_items if k in YOUTUBE_MEANINGFUL_QUERY and k != "v"}
            video_id = path.strip("/").split("/", 1)[0]
            if video_id:
                host = "youtube.com"
                path = "/watch"
                query_items = [("v", video_id)] + [(k, extras[k]) for k in ["t", "start", "time_continue", "list", "index"] if k in extras]
        if path == "/watch":
            params = {k: v for k, v in query_items if k in YOUTUBE_MEANINGFUL_QUERY}
            if "v" in params:
                # Keep deterministic key ordering for snapshot-friendly behavior.
                ordered_keys = [k for k in ["v", "t", "start", "time_continue", "list", "index"] if k in params]
                query_items = [(k, params[k]) for k in ordered_keys]
            else:
                query_items = []
            hash_t = _extract_timestamp_from_hash(parsed.fragment)
            if hash_t and not any(k in {"t", "start", "time_continue"} for k, _ in query_items):
                query_items.append(("t", hash_t))
        elif path.startswith("/shorts/"):
            short_id = path.split("/shorts/", 1)[-1].split("/", 1)[0]
            path = f"/shorts/{short_id}" if short_id else "/shorts"
            keep = {k for k in {"t"}}
            query_items = [(k, v) for k, v in query_items if k in keep]
        else:
            query_items = [(k, v) for k, v in query_items if k in MEDIA_INDEX_KEYS]
    elif platform_name == "linkedin":
        match = re.search(r"/feed/update/([^/?#]+)", path)
        if match:
            path = f"/feed/update/{match.group(1)}"
            query_items = []
        else:
            query_items = [(k, v) for k, v in query_items if k in MEDIA_INDEX_KEYS]
    elif platform_name == "facebook":
        if "/posts/" in path or "/permalink/" in path:
            query_items = [(k, v) for k, v in query_items if k in FACEBOOK_MEANINGFUL_QUERY]
        else:
            query_items = [(k, v) for k, v in query_items if k in FACEBOOK_MEANINGFUL_QUERY or k in MEDIA_INDEX_KEYS]
    elif platform_name == "tiktok":
        match = re.search(r"/@([^/]+)/video/(\d+)", path)
        if match:
            path = f"/@{match.group(1)}/video/{match.group(2)}"
        query_items = [(k, v) for k, v in query_items if k in MEDIA_INDEX_KEYS]
    else:
        query_items = [(k, v) for k, v in query_items if not _is_tracking_or_sensitive_key(k)]

    encoded_query = urlencode(query_items, doseq=True)
    return urlunparse((scheme, host, path, "", encoded_query, fragment))


def extract_post_id(url: str, platform: str = "unknown") -> str | None:
    if not url:
        return None
    try:
        parsed = urlparse(url)
    except Exception:
        return None

    path = parsed.path or ""
    query = dict(parse_qsl(parsed.query, keep_blank_values=False))
    platform_name = (platform or "unknown").strip().lower()

    if platform_name == "twitter":
        match = re.search(r"/status/(\d+)", path)
        return match.group(1) if match else None
    if platform_name == "youtube":
        if path == "/watch":
            return query.get("v")
        if path.startswith("/shorts/"):
            short_id = path.split("/shorts/", 1)[-1].split("/", 1)[0]
            return short_id or None
    if platform_name == "linkedin":
        match = re.search(r"/feed/update/([^/?#]+)", path)
        return match.group(1) if match else None
    if platform_name == "facebook":
        match = re.search(r"/posts/([^/?#]+)", path)
        if match:
            return match.group(1)
        match = re.search(r"/permalink/([^/?#]+)", path)
        if match:
            return match.group(1)
        return query.get("story_fbid")
    if platform_name == "tiktok":
        match = re.search(r"/video/(\d+)", path)
        return match.group(1) if match else None
    return None
