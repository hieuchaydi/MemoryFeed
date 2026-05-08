from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

# Isolate database paths before importing backend.server
_tmp = tempfile.mkdtemp(prefix="memoryfeed-admin-tests-")
os.environ["MEMORYFEED_DATA_DIR"] = _tmp
os.environ.setdefault("OFFLINE_ONLY", "1")
os.environ.setdefault("MEMORYFEED_AI_PROVIDER", "none")

from backend import server


class AdminEndpointAuthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(server.app)

    def test_admin_export_rejects_without_bearer(self) -> None:
        with patch.dict(os.environ, {"MEMORYFEED_ADMIN_TOKEN": "secret-token"}, clear=False):
            resp = self.client.post("/api/admin/export")
        self.assertEqual(resp.status_code, 401)

    def test_admin_export_accepts_valid_bearer(self) -> None:
        with patch.dict(os.environ, {"MEMORYFEED_ADMIN_TOKEN": "secret-token"}, clear=False):
            resp = self.client.post(
                "/api/admin/export",
                headers={"Authorization": "Bearer secret-token"},
            )
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertTrue(payload.get("ok"))
        self.assertTrue(Path(payload["file"]).exists())


if __name__ == "__main__":
    unittest.main()
