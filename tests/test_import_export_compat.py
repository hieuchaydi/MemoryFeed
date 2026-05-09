from __future__ import annotations

import unittest

from backend.import_export import export_payload, import_payload


class ImportExportCompatTests(unittest.TestCase):
    def test_export_includes_schema_version(self) -> None:
        payload = export_payload([{"id": "1", "url": "https://example.com"}])
        self.assertIn("schema_version", payload)
        self.assertIn("items", payload)

    def test_import_accepts_v1_without_schema_version(self) -> None:
        items, warnings = import_payload({"items": [{"id": "1", "url": "https://example.com"}]})
        self.assertEqual(len(items), 1)
        self.assertEqual(warnings, [])

    def test_import_skips_malformed_items(self) -> None:
        items, warnings = import_payload({"schema_version": "2", "items": ["bad", {"id": "2"}]})
        self.assertEqual(items, [])
        self.assertGreaterEqual(len(warnings), 1)


if __name__ == "__main__":
    unittest.main()
