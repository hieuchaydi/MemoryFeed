from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / "memoryfeed" / "__version__.py"
README_FILE = ROOT / "README.md"


def _read_package_version(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    return str(data["version"])


def _read_lock_root_version(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    return str(data["version"])


def _read_manifest_version(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    return str(data["version"])


def _read_python_version(path: Path) -> str:
    content = path.read_text(encoding="utf-8")
    m = re.search(r'__version__\s*=\s*"([^"]+)"', content)
    if not m:
        raise RuntimeError(f"Cannot parse __version__ from {path}")
    return m.group(1)


def _read_readme_badge_version(path: Path) -> str:
    content = path.read_text(encoding="utf-8")
    m = re.search(r"badge/version-([0-9]+\.[0-9]+\.[0-9]+)-blue\.svg", content)
    if not m:
        raise RuntimeError("Cannot parse version badge from README.md")
    return m.group(1)


def main() -> int:
    target = _read_python_version(VERSION_FILE)
    checks: list[tuple[str, str]] = [
        ("README badge", _read_readme_badge_version(README_FILE)),
        ("frontend/package.json", _read_package_version(ROOT / "frontend" / "package.json")),
        ("frontend/package-lock.json", _read_lock_root_version(ROOT / "frontend" / "package-lock.json")),
        ("docs-react/package.json", _read_package_version(ROOT / "docs-react" / "package.json")),
        ("docs-react/package-lock.json", _read_lock_root_version(ROOT / "docs-react" / "package-lock.json")),
        ("extension/chrome/manifest.json", _read_manifest_version(ROOT / "extension" / "chrome" / "manifest.json")),
        ("extension/firefox/manifest.json", _read_manifest_version(ROOT / "extension" / "firefox" / "manifest.json")),
    ]

    mismatches = [(name, version) for name, version in checks if version != target]
    if mismatches:
        print(f"Version sync check failed. Expected {target}.")
        for name, version in mismatches:
            print(f"- {name}: {version}")
        return 1

    print(f"Version sync OK: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
