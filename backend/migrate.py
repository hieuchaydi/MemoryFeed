from __future__ import annotations

import importlib
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from backend.db_connection import connect_db

DATA_DIR = Path(os.getenv("MEMORYFEED_DATA_DIR", str(Path.home() / ".memoryfeed"))).expanduser()
DB_PATH = DATA_DIR / "memoryfeed.db"


@dataclass(frozen=True)
class Migration:
    revision: int
    name: str
    module_name: str


def discover_migrations() -> list[Migration]:
    migrations_dir = Path(__file__).resolve().parent / "migrations"
    candidates = sorted(migrations_dir.glob("[0-9][0-9][0-9][0-9]_*.py"))
    out: list[Migration] = []
    for path in candidates:
        module_name = f"backend.migrations.{path.stem}"
        mod = importlib.import_module(module_name)
        revision = int(getattr(mod, "REVISION"))
        name = str(getattr(mod, "NAME", path.stem))
        out.append(Migration(revision=revision, name=name, module_name=module_name))
    out.sort(key=lambda m: m.revision)
    return out


def latest_schema_version() -> int:
    migrations = discover_migrations()
    return migrations[-1].revision if migrations else 0


def _ensure_meta_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
    )


def get_schema_version(conn: sqlite3.Connection) -> int:
    _ensure_meta_table(conn)
    row = conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
    if not row:
        return 0
    try:
        return int(str(row[0]))
    except ValueError:
        return 0


def set_schema_version(conn: sqlite3.Connection, version: int) -> None:
    conn.execute(
        """
        INSERT INTO meta(key, value)
        VALUES('schema_version', ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (str(int(version)),),
    )


def run_migrations_on_connection(conn: sqlite3.Connection, target_version: int | None = None) -> dict[str, Any]:
    _ensure_meta_table(conn)
    before = get_schema_version(conn)
    migrations = discover_migrations()
    if target_version is not None:
        migrations = [m for m in migrations if m.revision <= target_version]

    applied: list[dict[str, Any]] = []
    for migration in migrations:
        if migration.revision <= before:
            continue
        mod = importlib.import_module(migration.module_name)
        apply_fn = getattr(mod, "apply")
        apply_fn(conn)
        set_schema_version(conn, migration.revision)
        applied.append({"revision": migration.revision, "name": migration.name})
    after = get_schema_version(conn)
    return {
        "before": before,
        "after": after,
        "applied": applied,
        "latest": migrations[-1].revision if migrations else before,
    }


def run_migrations(db_path: Path | None = None, target_version: int | None = None) -> dict[str, Any]:
    db_file = db_path or DB_PATH
    db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = connect_db(db_file, check_same_thread=False)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        report = run_migrations_on_connection(conn, target_version=target_version)
        conn.commit()
        return report
    finally:
        conn.close()
