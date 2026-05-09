from __future__ import annotations

import unittest

from backend.memory_graph import derive_graph_fields


class MemoryGraphTests(unittest.TestCase):
    def test_graph_fields_are_derived_locally(self) -> None:
        out = derive_graph_fields({"text_content": "Discussing #Kubernetes with @alice about API gateways at CNCF"})
        self.assertTrue(out["related_topics"])
        self.assertTrue(out["related_entities"])
        self.assertIsNotNone(out["semantic_group"])


if __name__ == "__main__":
    unittest.main()
