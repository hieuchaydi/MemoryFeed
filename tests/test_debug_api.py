from __future__ import annotations

import importlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


class DebugApiTests(unittest.TestCase):
    def test_latest_capture_debug_endpoint_local_only(self) -> None:
        with tempfile.TemporaryDirectory(prefix="memoryfeed-debug-api-") as tmp:
            with patch.dict(os.environ, {"MEMORYFEED_DATA_DIR": str(Path(tmp))}, clear=False):
                import backend.server as server

                importlib.reload(server)
                inserted, _ = server.store.insert_item(
                    {
                        "id": "dbg-1",
                        "url": "https://example.com/post?token=abc",
                        "platform": "unknown",
                        "content_type": "post",
                        "text_content": "debug payload",
                        "captured_at": "2026-05-09T02:00:00+00:00",
                        "dedupe_key": "dbg-key-1",
                        "capture_debug": {"selector_used": {"text": "fallback:none"}, "missing_fields": []},
                        "capture_confidence": 0.7,
                    }
                )
                self.assertTrue(inserted)

                client = TestClient(server.app)
                resp = client.get("/api/debug/capture/latest")
                self.assertEqual(resp.status_code, 200)
                payload = resp.json()
                self.assertTrue(payload["ok"])
                self.assertEqual(payload["item"]["id"], "dbg-1")
                self.assertIn("selector_used", payload["item"])


if __name__ == "__main__":
    unittest.main()
