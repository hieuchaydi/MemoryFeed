from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"


def main() -> int:
    total = 0
    failed = 0
    for jf in FIXTURES.rglob("*.json"):
        total += 1
        try:
            payload = json.loads(jf.read_text(encoding="utf-8"))
        except Exception:
            print(f"FAIL parse {jf}")
            failed += 1
            continue
        missing = []
        for field in ["url", "platform", "text_content"]:
            if field not in payload:
                missing.append(field)
        if missing:
            print(f"FAIL {jf}: missing {','.join(missing)}")
            failed += 1
            continue
        qf = payload.get("quality_flags")
        if qf is not None and not isinstance(qf, list):
            print(f"FAIL {jf}: quality_flags must be list when present")
            failed += 1
            continue
    print(f"selector_replay total={total} failed={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
