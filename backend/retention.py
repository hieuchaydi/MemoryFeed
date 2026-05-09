from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


def run_retention_policy(
    conn,
    retention_days: int,
    low_score_threshold: float,
    auto_archive: bool = True,
) -> dict[str, Any]:
    if retention_days <= 0:
        return {"evaluated": 0, "archived": 0}

    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    rows = conn.execute(
        """
        SELECT id, captured_at, archived_at, importance_score, recency_score, starred
        FROM items
        WHERE captured_at <= ?
        """,
        (cutoff.isoformat(),),
    ).fetchall()

    evaluated = len(rows)
    if not auto_archive:
        return {"evaluated": evaluated, "archived": 0}

    archived = 0
    now_iso = datetime.now(timezone.utc).isoformat()
    for row in rows:
        if row["archived_at"]:
            continue
        if bool(row["starred"]):
            continue
        importance = float(row["importance_score"] or 0.0)
        recency = float(row["recency_score"] or 0.0)
        if importance > low_score_threshold:
            continue
        if recency > 0.25:
            continue
        conn.execute(
            """
            UPDATE items
            SET archived_at = ?, archive_reason = ?
            WHERE id = ? AND archived_at IS NULL
            """,
            (
                now_iso,
                f"retention:age>{retention_days}d,importance<={low_score_threshold:.2f}",
                row["id"],
            ),
        )
        archived += 1
    return {"evaluated": evaluated, "archived": archived}
