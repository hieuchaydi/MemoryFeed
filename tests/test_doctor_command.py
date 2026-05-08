from __future__ import annotations

import json
import unittest

from click.testing import CliRunner

from tests._util import ensure_test_data_dir

ensure_test_data_dir()

from cli import cli


class DoctorCommandTests(unittest.TestCase):
    def test_doctor_json_output_is_valid(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["doctor", "--format", "json"])
        self.assertEqual(result.exit_code, 0, msg=result.output)
        payload = json.loads(result.output)
        self.assertIn("status", payload)
        self.assertIn("checks", payload)
        self.assertIsInstance(payload["checks"], list)


if __name__ == "__main__":
    unittest.main()
