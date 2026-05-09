from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.memory_lifecycle import MemoryLifecycleEngine


class MemoryLifecycleEngineTests(unittest.TestCase):
    def test_lifecycle_crud_flow(self) -> None:
        with tempfile.NamedTemporaryFile(prefix="memoryfeed-lifecycle-", suffix=".db", delete=False) as tmp:
            db_path = Path(tmp.name)
        try:
            engine = MemoryLifecycleEngine(db_path)
            item = {
                "id": "abc-1",
                "text_content": "Docker compose runbook and deployment notes",
                "capture_confidence": 0.9,
                "importance_score": 0.6,
                "captured_at": "2026-01-01T00:00:00+00:00",
            }
            memory_id = engine.ensure_memory_for_item(item)
            engine.summarize_memory(memory_id, item["text_content"])
            engine.reinforce_memory(memory_id, delta=0.2)
            engine.apply_decay_cycle(item)
            conflict_id = engine.report_conflict(memory_id, "status", "draft", "final", 0.2, 0.8)
            self.assertTrue(conflict_id)

            timeline = engine.timeline(50)
            self.assertGreaterEqual(len(timeline), 4)

            aging = engine.aging(10)
            self.assertGreaterEqual(len(aging), 1)
        finally:
            pass


if __name__ == "__main__":
    unittest.main()
