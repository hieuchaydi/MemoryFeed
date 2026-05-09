from __future__ import annotations

import importlib
import os
import unittest
from unittest.mock import patch

import backend.dedupe as dedupe
import backend.runtime_config as runtime_config


class DedupeWindowTests(unittest.TestCase):
    def test_global_dedupe_window_respects_env(self) -> None:
        with patch.dict(os.environ, {"MEMORY_DEDUPE_WINDOW_HOURS": "4", "MEMORY_PLATFORM_DEDUPE_WINDOWS": ""}, clear=False):
            importlib.reload(runtime_config)
            importlib.reload(dedupe)
            bucket_a = dedupe.dedupe_bucket("2026-05-08T00:30:00+00:00", platform="twitter")
            bucket_b = dedupe.dedupe_bucket("2026-05-08T03:59:59+00:00", platform="twitter")
            bucket_c = dedupe.dedupe_bucket("2026-05-08T04:00:01+00:00", platform="twitter")
            self.assertEqual(bucket_a, bucket_b)
            self.assertNotEqual(bucket_a, bucket_c)

    def test_platform_override_and_malformed_json_fallback(self) -> None:
        with patch.dict(
            os.environ,
            {
                "MEMORY_DEDUPE_WINDOW_HOURS": "2",
                "MEMORY_PLATFORM_DEDUPE_WINDOWS": "{\"youtube\":12,\"twitter\":1}",
            },
            clear=False,
        ):
            importlib.reload(runtime_config)
            importlib.reload(dedupe)
            twitter_a = dedupe.dedupe_bucket("2026-05-08T00:15:00+00:00", platform="twitter")
            twitter_b = dedupe.dedupe_bucket("2026-05-08T01:20:00+00:00", platform="twitter")
            self.assertNotEqual(twitter_a, twitter_b)

            youtube_a = dedupe.dedupe_bucket("2026-05-08T00:15:00+00:00", platform="youtube")
            youtube_b = dedupe.dedupe_bucket("2026-05-08T11:20:00+00:00", platform="youtube")
            self.assertEqual(youtube_a, youtube_b)

        with patch.dict(
            os.environ,
            {"MEMORY_DEDUPE_WINDOW_HOURS": "2", "MEMORY_PLATFORM_DEDUPE_WINDOWS": "{bad-json"},
            clear=False,
        ):
            importlib.reload(runtime_config)
            cfg = runtime_config.load_runtime_config()
            self.assertEqual(cfg.memory_platform_dedupe_windows, {})


if __name__ == "__main__":
    unittest.main()
