from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

_ROOT = Path(__file__).resolve().parent.parent
SELECTOR_DIR = _ROOT / "extension" / "selectors"
FIXTURE_DIR = _ROOT / "tests" / "fixtures"


@dataclass
class ReplayResult:
    fixture: str
    platform: str
    extracted: dict[str, Any]
    selector_used: dict[str, Any]
    missing_fields: list[str]
    quality_flags: list[str]
    expected: dict[str, Any] | None
    matches_expected: bool
    mismatch_keys: list[str]
    deterministic: bool
    replay_timestamp: str


class _Node:
    def __init__(self, tag: str, attrs: dict[str, str], parent: "_Node | None") -> None:
        self.tag = (tag or "").lower()
        self.attrs = {k.lower(): v for k, v in attrs.items()}
        self.parent = parent
        self.children: list[_Node] = []
        self.text_chunks: list[str] = []

    def text_content(self) -> str:
        own = " ".join(self.text_chunks).strip()
        child = " ".join(child.text_content() for child in self.children).strip()
        out = " ".join(part for part in [own, child] if part).strip()
        return re.sub(r"\s+", " ", out).strip()

    def attr(self, name: str) -> str:
        return self.attrs.get(name.lower(), "")


class _MiniDomParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _Node("document", {}, None)
        self.stack: list[_Node] = [self.root]
        self.nodes: list[_Node] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = _Node(tag, {k: (v or "") for k, v in attrs}, self.stack[-1])
        self.stack[-1].children.append(node)
        self.stack.append(node)
        self.nodes.append(node)

    def handle_endtag(self, tag: str) -> None:
        lowered = (tag or "").lower()
        for idx in range(len(self.stack) - 1, 0, -1):
            if self.stack[idx].tag == lowered:
                del self.stack[idx:]
                return
        if len(self.stack) > 1:
            self.stack.pop()

    def handle_data(self, data: str) -> None:
        if data and self.stack:
            self.stack[-1].text_chunks.append(data)


_ATTR_RE = re.compile(r"\[([^\]]+)\]")
_ID_RE = re.compile(r"#([A-Za-z0-9_-]+)")
_CLASS_RE = re.compile(r"\.([A-Za-z0-9_-]+)")


def _parse_selector_token(token: str) -> dict[str, Any]:
    s = token.strip()
    tag_match = re.match(r"^[A-Za-z0-9_-]+", s)
    tag = tag_match.group(0).lower() if tag_match else ""
    ids = [m.group(1) for m in _ID_RE.finditer(s)]
    classes = [m.group(1) for m in _CLASS_RE.finditer(s)]

    attrs: list[tuple[str, str, str]] = []
    for raw in _ATTR_RE.findall(s):
        if "*=" in raw:
            key, value = raw.split("*=", 1)
            attrs.append((key.strip().lower(), "contains", value.strip("'\"")))
        elif "^=" in raw:
            key, value = raw.split("^=", 1)
            attrs.append((key.strip().lower(), "starts", value.strip("'\"")))
        elif "$=" in raw:
            key, value = raw.split("$=", 1)
            attrs.append((key.strip().lower(), "ends", value.strip("'\"")))
        elif "=" in raw:
            key, value = raw.split("=", 1)
            attrs.append((key.strip().lower(), "equals", value.strip("'\"")))
        else:
            attrs.append((raw.strip().lower(), "exists", ""))
    return {"tag": tag, "ids": ids, "classes": classes, "attrs": attrs}


def _match_token(node: _Node, token: dict[str, Any]) -> bool:
    if token["tag"] and node.tag != token["tag"]:
        return False
    for expected_id in token["ids"]:
        if node.attr("id") != expected_id:
            return False
    if token["classes"]:
        class_set = set(node.attr("class").split())
        if not all(cls in class_set for cls in token["classes"]):
            return False
    for key, op, value in token["attrs"]:
        actual = node.attr(key)
        if op == "exists" and key not in node.attrs:
            return False
        if op == "equals" and actual != value:
            return False
        if op == "contains" and value not in actual:
            return False
        if op == "starts" and not actual.startswith(value):
            return False
        if op == "ends" and not actual.endswith(value):
            return False
    return True


def _selector_tokens(selector: str) -> list[dict[str, Any]]:
    return [_parse_selector_token(part) for part in selector.strip().split() if part.strip()]


def _node_matches_selector(node: _Node, selector: str) -> bool:
    parts = _selector_tokens(selector)
    if not parts:
        return False
    if not _match_token(node, parts[-1]):
        return False
    current_parent = node.parent
    for idx in range(len(parts) - 2, -1, -1):
        wanted = parts[idx]
        found = False
        while current_parent is not None:
            if _match_token(current_parent, wanted):
                found = True
                current_parent = current_parent.parent
                break
            current_parent = current_parent.parent
        if not found:
            return False
    return True


def _find_nodes(dom: _MiniDomParser, selector: str) -> list[_Node]:
    selectors = [part.strip() for part in selector.split(",") if part.strip()]
    out: list[_Node] = []
    for node in dom.nodes:
        if any(_node_matches_selector(node, part) for part in selectors):
            out.append(node)
    return out


def _read_node_text(node: _Node, selector: str) -> str:
    if selector.strip().startswith("meta["):
        return (node.attr("content") or "").strip()
    return node.text_content().strip()


def _read_node_url(node: _Node, selector: str) -> str:
    stripped = selector.strip()
    if stripped.startswith("meta["):
        return node.attr("content").strip()
    if stripped.startswith("link["):
        return node.attr("href").strip()
    if node.tag == "a":
        return (node.attr("href") or "").strip()
    if node.tag in {"img", "source", "video"}:
        return (node.attr("src") or node.attr("poster") or "").strip()
    return (node.attr("href") or node.attr("src") or "").strip()


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _normalize_abs_url(value: str, base_url: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    if raw.startswith(("http://", "https://")):
        return raw
    if raw.startswith("//"):
        scheme = "https" if base_url.startswith("https://") else "http"
        return f"{scheme}:{raw}"
    if raw.startswith("/"):
        parsed = urlparse(base_url)
        return f"{parsed.scheme}://{parsed.netloc}{raw}"
    return raw


def _load_selector_config(platform: str) -> dict[str, Any]:
    path = SELECTOR_DIR / f"{platform}.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing selector file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _first_text(dom: _MiniDomParser, selectors: list[str], fallback: list[str]) -> tuple[str, str]:
    for selector in [*selectors, *fallback]:
        nodes = _find_nodes(dom, selector)
        for node in nodes:
            text = _clean_text(_read_node_text(node, selector))
            if text:
                return text, selector
    return "", ""


def _first_url(dom: _MiniDomParser, selectors: list[str], fallback: list[str], base_url: str) -> tuple[str, str]:
    for selector in [*selectors, *fallback]:
        nodes = _find_nodes(dom, selector)
        for node in nodes:
            url = _normalize_abs_url(_read_node_url(node, selector), base_url)
            if url:
                return url, selector
    return "", ""


def _collect_urls(
    dom: _MiniDomParser,
    selectors: list[str],
    fallback: list[str],
    base_url: str,
    limit: int = 8,
) -> tuple[list[str], list[str]]:
    seen: set[str] = set()
    output: list[str] = []
    used: list[str] = []
    for selector in [*selectors, *fallback]:
        nodes = _find_nodes(dom, selector)
        for node in nodes:
            url = _normalize_abs_url(_read_node_url(node, selector), base_url)
            if not url or url in seen:
                continue
            seen.add(url)
            output.append(url)
            used.append(selector)
            if len(output) >= limit:
                return output, list(dict.fromkeys(used))
    return output, list(dict.fromkeys(used))


def replay_fixture(
    fixture_html: str | Path,
    expected_snapshot: str | Path | None = None,
    deterministic: bool = False,
) -> ReplayResult:
    html_path = Path(fixture_html)
    content = html_path.read_text(encoding="utf-8")
    fixture_name = html_path.name
    platform = fixture_name.split("_", 1)[0].replace(".html", "").lower()
    if platform not in {"facebook", "twitter", "youtube", "linkedin", "tiktok"}:
        platform = "unknown"

    cfg = _load_selector_config(platform)
    fallback = cfg.get("fallback_selectors") or {}
    base_url = cfg.get("fixture_base_url") or "https://example.com/"

    dom = _MiniDomParser()
    dom.feed(content)

    text, text_selector = _first_text(dom, cfg.get("text_selectors") or [], fallback.get("text") or [])
    author, author_selector = _first_text(dom, cfg.get("author_selectors") or [], fallback.get("author_name") or [])
    handle, handle_selector = _first_text(dom, cfg.get("author_handle_selectors") or [], fallback.get("author_handle") or [])
    canonical_url, url_selector = _first_url(
        dom,
        cfg.get("canonical_url_selectors") or [],
        fallback.get("canonical_url") or [],
        base_url=base_url,
    )
    media_urls, media_selectors = _collect_urls(
        dom,
        cfg.get("media_selectors") or [],
        fallback.get("media") or [],
        base_url=base_url,
    )
    if deterministic:
        media_urls = sorted(media_urls)
        media_selectors = sorted(dict.fromkeys(media_selectors))
    replay_timestamp = "2024-01-01T00:00:00+00:00" if deterministic else datetime.now(timezone.utc).isoformat()
    canonical = canonical_url or base_url
    required = {
        "platform": platform,
        "canonical_url": canonical,
        "author_name": author,
        "text": text,
        "media_urls": media_urls,
    }
    missing_fields = [
        key
        for key, value in required.items()
        if (not value) or (isinstance(value, list) and not value)
    ]
    quality_flags = [f"missing_{key}" for key in missing_fields]
    if deterministic:
        quality_flags = sorted(quality_flags)

    extracted = {
        "platform": platform,
        "url": canonical,
        "canonical_url": canonical,
        "text_content": text,
        "author_name": author or None,
        "author_handle": handle or None,
        "media_urls": media_urls[:6],
        "quality_flags": quality_flags,
    }
    if deterministic:
        extracted["captured_at"] = replay_timestamp
    selector_used = {
        "text": text_selector or "fallback:none",
        "author_name": author_selector or "fallback:none",
        "author_handle": handle_selector or "fallback:none",
        "canonical_url": url_selector or "fallback:none",
        "media_urls": media_selectors,
    }

    expected_path: Path | None = None
    if expected_snapshot:
        expected_path = Path(expected_snapshot)
    else:
        maybe = html_path.with_suffix(".json")
        if maybe.exists():
            expected_path = maybe

    expected: dict[str, Any] | None = None
    mismatch_keys: list[str] = []
    if expected_path and expected_path.exists():
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
        for key, expected_val in expected.items():
            if key == "captured_at" and not deterministic:
                continue
            if extracted.get(key) != expected_val:
                mismatch_keys.append(key)
    return ReplayResult(
        fixture=str(html_path),
        platform=platform,
        extracted=extracted,
        selector_used=selector_used,
        missing_fields=missing_fields,
        quality_flags=quality_flags,
        expected=expected,
        matches_expected=not mismatch_keys,
        mismatch_keys=mismatch_keys,
        deterministic=deterministic,
        replay_timestamp=replay_timestamp,
    )


def test_platform_fixtures(
    platform: str,
    fixture_dir: Path | None = None,
    deterministic: bool = False,
) -> dict[str, Any]:
    directory = fixture_dir or FIXTURE_DIR
    root_files = sorted(directory.glob(f"{platform}_*.html"))
    nested_files = sorted((directory / platform).glob("*.html")) if (directory / platform).exists() else []
    files = sorted(root_files + nested_files)
    results = [replay_fixture(path, deterministic=deterministic) for path in files]
    return {
        "platform": platform,
        "deterministic": deterministic,
        "fixtures": len(results),
        "passed": sum(1 for row in results if row.matches_expected),
        "failed": sum(1 for row in results if not row.matches_expected),
        "results": [
            {
                "fixture": row.fixture,
                "matches_expected": row.matches_expected,
                "mismatch_keys": row.mismatch_keys,
                "missing_fields": row.missing_fields,
                "quality_flags": row.quality_flags,
                "selector_used": row.selector_used,
                "extracted": row.extracted,
            }
            for row in results
        ],
    }
