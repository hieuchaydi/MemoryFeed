from __future__ import annotations

import asyncio
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

_tmp = tempfile.mkdtemp(prefix="memoryfeed-public-tls-")
os.environ["MEMORYFEED_DATA_DIR"] = _tmp
os.environ.setdefault("OFFLINE_ONLY", "1")
os.environ.setdefault("MEMORYFEED_AI_PROVIDER", "none")

from backend import server


class PublicModeTlsTests(unittest.TestCase):
    def test_public_mode_requires_tls_termination(self) -> None:
        with patch.dict(
            os.environ,
            {
                "MEMORYFEED_PUBLIC_MODE": "1",
                "MEMORYFEED_PUBLIC_REQUIRE_TLS": "1",
                "MEMORYFEED_BIND_HOST": "0.0.0.0",
                "MEMORYFEED_TLS_TERMINATED": "0",
            },
            clear=False,
        ):
            with self.assertRaises(RuntimeError):
                asyncio.run(server.startup_event())

    def test_public_mode_allows_start_when_tls_terminated(self) -> None:
        with patch.dict(
            os.environ,
            {
                "MEMORYFEED_PUBLIC_MODE": "1",
                "MEMORYFEED_PUBLIC_REQUIRE_TLS": "1",
                "MEMORYFEED_BIND_HOST": "0.0.0.0",
                "MEMORYFEED_TLS_TERMINATED": "1",
            },
            clear=False,
        ):
            with patch.object(server.indexer, "start", new=AsyncMock()), patch.object(
                server.vision, "start", new=AsyncMock()
            ), patch.object(server.maintenance, "start", new=AsyncMock()):
                asyncio.run(server.startup_event())


if __name__ == "__main__":
    unittest.main()
