from __future__ import annotations

import os
import unittest

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from tests._util import ensure_test_data_dir

ensure_test_data_dir()
os.environ.setdefault("OFFLINE_ONLY", "1")
os.environ.setdefault("MEMORYFEED_AI_PROVIDER", "none")

from backend.server import require_sensitive_access


class AdminAuthTests(unittest.TestCase):
    def setUp(self) -> None:
        app = FastAPI()

        @app.post("/protected", dependencies=[Depends(require_sensitive_access)])
        def protected_endpoint() -> dict[str, bool]:
            return {"ok": True}

        self.client = TestClient(app)

    def test_rejects_missing_token_when_configured(self) -> None:
        os.environ["MEMORYFEED_ADMIN_TOKEN"] = "unit-test-token"
        resp = self.client.post("/protected")
        self.assertEqual(resp.status_code, 401)

    def test_accepts_valid_bearer_token(self) -> None:
        os.environ["MEMORYFEED_ADMIN_TOKEN"] = "unit-test-token"
        resp = self.client.post(
            "/protected",
            headers={"Authorization": "Bearer unit-test-token"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"ok": True})


if __name__ == "__main__":
    unittest.main()
