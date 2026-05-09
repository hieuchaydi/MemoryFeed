from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

from backend.maintenance import MaintenanceScheduler
from backend.store import Store


class MaintenanceTests(unittest.TestCase):
    def test_maintenance_run_once_returns_task_summary(self) -> None:
        with tempfile.TemporaryDirectory(prefix="memoryfeed-maint-") as tmp:
            store = Store(db_path=Path(tmp) / "memoryfeed.db")
            store.insert_item(
                {
                    "id": "m1",
                    "url": "https://example.com/1",
                    "platform": "unknown",
                    "content_type": "post",
                    "text_content": "maintenance check",
                    "captured_at": "2026-05-09T10:00:00+00:00",
                }
            )
            scheduler = MaintenanceScheduler(store)
            summary = asyncio.run(scheduler.run_once())
            self.assertIn("rebuilt_fingerprints", summary)
            self.assertIn("compacted_indexes", summary)
            self.assertIn("logs_cleaned", summary)


if __name__ == "__main__":
    unittest.main()
