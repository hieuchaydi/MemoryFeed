from __future__ import annotations

import os
import tempfile
from pathlib import Path


def ensure_test_data_dir() -> str:
    existing = os.getenv("MEMORYFEED_DATA_DIR")
    if existing:
        Path(existing).mkdir(parents=True, exist_ok=True)
        return existing
    tmp = tempfile.mkdtemp(prefix="memoryfeed-tests-")
    os.environ["MEMORYFEED_DATA_DIR"] = tmp
    return tmp
