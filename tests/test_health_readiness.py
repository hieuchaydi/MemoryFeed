from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

_tmp = tempfile.mkdtemp(prefix="memoryfeed-health-tests-")
os.environ["MEMORYFEED_DATA_DIR"] = _tmp
os.environ.setdefault("OFFLINE_ONLY", "1")
os.environ.setdefault("MEMORYFEED_AI_PROVIDER", "none")

from backend import server


class HealthReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(server.app)

    def test_healthz_has_db_flag(self) -> None:
        resp = self.client.get("/healthz")
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertIn("db_ok", payload)

    def test_readyz_includes_db_encryption_status(self) -> None:
        resp = self.client.get("/readyz")
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertIn("db_ok", payload)
        self.assertIn("db_encryption", payload)

    def test_admin_media_migrate_requires_auth_when_token_enabled(self) -> None:
        with patch.dict(os.environ, {"MEMORYFEED_ADMIN_TOKEN": "secret-token"}, clear=False):
            resp = self.client.post("/api/admin/encryption/migrate-media")
        self.assertEqual(resp.status_code, 401)


if __name__ == "__main__":
    unittest.main()
