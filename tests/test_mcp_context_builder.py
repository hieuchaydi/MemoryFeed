from __future__ import annotations

import unittest

from backend.mcp_server import _build_rag_context, _extract_context_text


class McpContextBuilderTests(unittest.TestCase):
    def test_extract_context_text_compacts_whitespace_and_truncates(self) -> None:
        text = "hello   world\n\nfrom   memoryfeed"
        self.assertEqual(_extract_context_text({"text_content": text}, max_chars=22), "hello world from me...")

    def test_build_rag_context_returns_citations_and_context_lines(self) -> None:
        rows = [
            {
                "id": "1",
                "platform": "twitter",
                "captured_at": "2026-05-12T10:00:00+00:00",
                "url": "https://x.com/a/1",
                "text_content": "first memory result",
            },
            {
                "id": "2",
                "platform": "reddit",
                "captured_at": "2026-05-11T10:00:00+00:00",
                "url": "https://reddit.com/r/test/2",
                "text_excerpt": "second memory result",
            },
        ]
        context, citations = _build_rag_context(rows, max_context_chars=1000)
        self.assertIn("[1] (twitter, 2026-05-12T10:00:00+00:00) first memory result", context)
        self.assertIn("source=https://x.com/a/1", context)
        self.assertIn("[2] (reddit, 2026-05-11T10:00:00+00:00) second memory result", context)
        self.assertEqual(len(citations), 2)
        self.assertEqual(citations[0]["rank"], 1)
        self.assertEqual(citations[1]["rank"], 2)

    def test_build_rag_context_enforces_character_budget(self) -> None:
        rows = [
            {
                "id": "1",
                "platform": "twitter",
                "captured_at": "2026-05-12T10:00:00+00:00",
                "url": "https://x.com/a/1",
                "text_content": "a" * 220,
            },
            {
                "id": "2",
                "platform": "twitter",
                "captured_at": "2026-05-12T11:00:00+00:00",
                "url": "https://x.com/a/2",
                "text_content": "b" * 220,
            },
        ]
        context, citations = _build_rag_context(rows, max_context_chars=520)
        self.assertEqual(len(citations), 1)
        self.assertIn("source=https://x.com/a/1", context)
        self.assertNotIn("source=https://x.com/a/2", context)

    def test_build_rag_context_fallback_when_no_text(self) -> None:
        rows = [{"id": "1", "platform": "twitter", "captured_at": "2026-05-12T10:00:00+00:00"}]
        context, citations = _build_rag_context(rows)
        self.assertEqual(context, "No relevant memory context found.")
        self.assertEqual(citations, [])


if __name__ == "__main__":
    unittest.main()
