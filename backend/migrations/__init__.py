from __future__ import annotations

import sqlite3
from typing import Iterable


def ensure_column(conn: sqlite3.Connection, table: str, col_name: str, col_type: str) -> None:
    cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
    names = {row[1] for row in cols}
    if col_name not in names:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")


def ensure_indexes(conn: sqlite3.Connection, statements: Iterable[str]) -> None:
    for sql in statements:
        conn.execute(sql)
