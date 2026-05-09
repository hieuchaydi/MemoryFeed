from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.db_connection import connect_db, sqlcipher_status
from backend.store import Store


class DbEncryptionRuntimeTests(unittest.TestCase):
    def test_sqlcipher_status_disabled_by_default(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            status = sqlcipher_status()
            self.assertIn("enabled", status)
            self.assertIn("active", status)
            self.assertFalse(bool(status["enabled"]))

    def test_store_ping_returns_true(self) -> None:
        with tempfile.TemporaryDirectory(prefix="memoryfeed-db-ping-") as tmp:
            db_path = Path(tmp) / "memoryfeed.db"
            store = Store(db_path=db_path)
            self.assertTrue(store.ping())

    def test_connect_db_fallback_sqlite(self) -> None:
        with tempfile.TemporaryDirectory(prefix="memoryfeed-db-conn-") as tmp:
            db_path = Path(tmp) / "fallback.db"
            with patch.dict(
                os.environ,
                {"MEMORY_SQLCIPHER_ENABLED": "0", "MEMORY_SQLCIPHER_KEY": ""},
                clear=False,
            ):
                conn = connect_db(db_path)
                try:
                    conn.execute("CREATE TABLE IF NOT EXISTS t (id INTEGER PRIMARY KEY, v TEXT)")
                    conn.execute("INSERT INTO t(v) VALUES('ok')")
                    row = conn.execute("SELECT COUNT(*) FROM t").fetchone()
                    self.assertIsNotNone(row)
                finally:
                    conn.close()


if __name__ == "__main__":
    unittest.main()
