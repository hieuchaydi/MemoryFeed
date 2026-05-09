from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests._util import ensure_test_data_dir

ensure_test_data_dir()

from backend.migrate import run_migrations
from backend.store import Store


class MigrationTests(unittest.TestCase):
    def test_migration_runner_applies_latest_schema(self) -> None:
        with tempfile.TemporaryDirectory(prefix="memoryfeed-migrate-") as tmp:
            db_path = Path(tmp) / "memoryfeed.db"
            report = run_migrations(db_path=db_path)
            self.assertGreaterEqual(report["after"], 5)
            self.assertGreaterEqual(len(report["applied"]), 1)

            store = Store(db_path=db_path)
            self.assertEqual(store.schema_version(), report["after"])


if __name__ == "__main__":
    unittest.main()
