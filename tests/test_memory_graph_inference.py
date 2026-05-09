from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.memory_lifecycle import MemoryLifecycleEngine


class MemoryGraphInferenceTests(unittest.TestCase):
    def test_infer_support_edges(self) -> None:
        with tempfile.NamedTemporaryFile(prefix="memoryfeed-graph-", suffix=".db", delete=False) as tmp:
            db_path = Path(tmp.name)
        engine = MemoryLifecycleEngine(db_path)

        item_a = {
            "id": "g-1",
            "text_content": "Docker on Kubernetes rollout plan",
            "capture_confidence": 0.9,
            "importance_score": 0.7,
            "related_entities": ["kubernetes"],
            "related_topics": ["docker"],
            "namespace": "default",
        }
        item_b = {
            "id": "g-2",
            "text_content": "Kubernetes migration checklist",
            "capture_confidence": 0.9,
            "importance_score": 0.7,
            "related_entities": ["kubernetes"],
            "related_topics": ["migration"],
            "namespace": "default",
        }

        mem_a = engine.ensure_memory_for_item(item_a)
        engine.summarize_memory(mem_a, item_a["text_content"])
        mem_b = engine.ensure_memory_for_item(item_b)
        engine.summarize_memory(mem_b, item_b["text_content"])

        edges = engine.infer_relations_for_item(item_b)
        self.assertTrue(any(edge.get("relation") in {"supports", "same_as", "contradicts"} for edge in edges))


if __name__ == "__main__":
    unittest.main()
