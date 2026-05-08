from __future__ import annotations

import importlib
import os
import unittest
from unittest.mock import patch

from tests._util import ensure_test_data_dir

ensure_test_data_dir()

import backend.llm_clients as llm_clients


class OfflineProviderTests(unittest.TestCase):
    def test_offline_mode_skips_connectivity_calls(self) -> None:
        with patch.dict(
            os.environ,
            {
                "OFFLINE_ONLY": "1",
                "MEMORYFEED_AI_PROVIDER": "auto",
                "GEMINI_API_KEY": "dummy",
                "GROQ_API_KEY": "dummy",
            },
            clear=False,
        ):
            importlib.reload(llm_clients)
            with patch("backend.llm_clients.httpx.get") as mocked_get:
                gemini_ok, gemini_reason = llm_clients.check_gemini_connectivity(timeout_s=0.1)
                groq_ok, groq_reason = llm_clients.check_groq_connectivity(timeout_s=0.1)

            self.assertTrue(gemini_ok)
            self.assertTrue(groq_ok)
            self.assertIn("Disabled", gemini_reason)
            self.assertIn("Disabled", groq_reason)
            mocked_get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
