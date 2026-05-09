from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.retention import compute_decay


MEMORY_STATES = {
    "captured",
    "normalized",
    "summarized",
    "indexed",
    "reinforced",
    "decaying",
    "archived",
    "forgotten",
}


@dataclass(frozen=True)
class LifecyclePolicy:
    summarize_max_chars: int = 560
    forget_decay_threshold: float = 0.97
    archive_decay_threshold: float = 0.85


class MemoryLifecycleEngine:
    def __init__(self, db_path: Path, policy: LifecyclePolicy | None = None) -> None:
        self.db_path = db_path
        self.policy = policy or LifecyclePolicy()
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_events (
                    event_id TEXT PRIMARY KEY,
                    memory_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload TEXT,
                    created_at TEXT NOT NULL
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_nodes (
                    memory_id TEXT PRIMARY KEY,
                    item_id TEXT,
                    state TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    summary_short TEXT,
                    summary_medium TEXT,
                    summary_long TEXT,
                    confidence REAL DEFAULT 1.0,
                    reinforcement REAL DEFAULT 0.0,
                    decay_score REAL DEFAULT 0.0,
                    importance_score REAL DEFAULT 0.0,
                    last_accessed_at TEXT,
                    forgotten_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_edges (
                    edge_id TEXT PRIMARY KEY,
                    from_memory_id TEXT NOT NULL,
                    to_memory_id TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    confidence REAL DEFAULT 1.0,
                    created_at TEXT NOT NULL
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_conflicts (
                    conflict_id TEXT PRIMARY KEY,
                    memory_id TEXT NOT NULL,
                    field_name TEXT NOT NULL,
                    value_a TEXT,
                    value_b TEXT,
                    confidence_a REAL DEFAULT 0.5,
                    confidence_b REAL DEFAULT 0.5,
                    resolved_value TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    resolved_at TEXT
                );
                """
            )
            conn.commit()

    def _event(self, conn: sqlite3.Connection, memory_id: str, event_type: str, payload: dict[str, Any] | None = None) -> str:
        event_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO memory_events(event_id, memory_id, event_type, payload, created_at) VALUES(?, ?, ?, ?, ?)",
            (event_id, memory_id, event_type, json.dumps(payload or {}, ensure_ascii=False), self._now()),
        )
        return event_id

    def ensure_memory_for_item(self, item: dict[str, Any]) -> str:
        memory_id = f"mem:{item['id']}"
        now = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO memory_nodes(memory_id, item_id, state, memory_type, confidence, importance_score, created_at, updated_at)
                VALUES(?, ?, 'captured', ?, ?, ?, ?, ?)
                ON CONFLICT(memory_id) DO NOTHING
                """,
                (
                    memory_id,
                    item["id"],
                    _memory_type(item),
                    float(item.get("capture_confidence") or 1.0),
                    float(item.get("importance_score") or 0.0),
                    now,
                    now,
                ),
            )
            self._event(conn, memory_id, "capture", {"item_id": item["id"]})
            conn.commit()
        return memory_id

    def summarize_memory(self, memory_id: str, text: str) -> None:
        short = _clip(text, 180)
        medium = _clip(text, 420)
        long = _clip(text, self.policy.summarize_max_chars)
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE memory_nodes
                SET summary_short=?, summary_medium=?, summary_long=?, state='summarized', updated_at=?
                WHERE memory_id=?
                """,
                (short, medium, long, self._now(), memory_id),
            )
            self._event(conn, memory_id, "summarize", {"len": len(text or "")})
            conn.commit()

    def reinforce_memory(self, memory_id: str, delta: float = 0.1) -> None:
        delta_v = max(-1.0, min(1.0, float(delta)))
        with self._connect() as conn:
            row = conn.execute("SELECT reinforcement FROM memory_nodes WHERE memory_id=?", (memory_id,)).fetchone()
            current = float(row["reinforcement"]) if row else 0.0
            nxt = max(0.0, min(10.0, current + delta_v))
            conn.execute(
                "UPDATE memory_nodes SET reinforcement=?, state='reinforced', last_accessed_at=?, updated_at=? WHERE memory_id=?",
                (nxt, self._now(), self._now(), memory_id),
            )
            self._event(conn, memory_id, "reinforce", {"delta": delta_v, "next": nxt})
            conn.commit()

    def apply_decay_cycle(self, item: dict[str, Any]) -> None:
        memory_id = f"mem:{item['id']}"
        decay_score, aging_state = compute_decay(item)
        next_state = "decaying"
        if aging_state == "archived":
            next_state = "archived"
        with self._connect() as conn:
            conn.execute(
                "UPDATE memory_nodes SET decay_score=?, state=?, updated_at=? WHERE memory_id=?",
                (float(decay_score), next_state, self._now(), memory_id),
            )
            self._event(conn, memory_id, "decay", {"decay_score": decay_score, "aging_state": aging_state})
            conn.commit()

    def forget_eligible(self) -> int:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT memory_id, decay_score FROM memory_nodes WHERE forgotten_at IS NULL"
            ).fetchall()
            forgotten = 0
            now = self._now()
            for row in rows:
                if float(row["decay_score"] or 0.0) >= self.policy.forget_decay_threshold:
                    conn.execute(
                        "UPDATE memory_nodes SET state='forgotten', forgotten_at=?, updated_at=? WHERE memory_id=?",
                        (now, now, row["memory_id"]),
                    )
                    self._event(conn, str(row["memory_id"]), "forget", {"reason": "decay_threshold"})
                    forgotten += 1
            conn.commit()
            return forgotten

    def merge_memories(self, primary_memory_id: str, secondary_memory_id: str, confidence: float = 0.8) -> str:
        edge_id = str(uuid.uuid4())
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO memory_edges(edge_id, from_memory_id, to_memory_id, relation, confidence, created_at) VALUES(?, ?, ?, 'same_as', ?, ?)",
                (edge_id, secondary_memory_id, primary_memory_id, float(confidence), self._now()),
            )
            self._event(conn, primary_memory_id, "merge", {"from": secondary_memory_id, "confidence": confidence})
            conn.commit()
        return edge_id

    def report_conflict(
        self,
        memory_id: str,
        field_name: str,
        value_a: str,
        value_b: str,
        confidence_a: float,
        confidence_b: float,
    ) -> str:
        conflict_id = str(uuid.uuid4())
        status = "open"
        resolved_value = None
        if abs(confidence_a - confidence_b) >= 0.25:
            status = "resolved"
            resolved_value = value_a if confidence_a >= confidence_b else value_b
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO memory_conflicts(
                    conflict_id, memory_id, field_name, value_a, value_b,
                    confidence_a, confidence_b, resolved_value, status, created_at, resolved_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    conflict_id,
                    memory_id,
                    field_name,
                    value_a,
                    value_b,
                    float(confidence_a),
                    float(confidence_b),
                    resolved_value,
                    status,
                    self._now(),
                    self._now() if status == "resolved" else None,
                ),
            )
            self._event(conn, memory_id, "conflict", {"field": field_name, "status": status})
            conn.commit()
        return conflict_id

    def timeline(self, limit: int = 200) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT event_id, memory_id, event_type, payload, created_at FROM memory_events ORDER BY created_at DESC LIMIT ?",
                (int(limit),),
            ).fetchall()
            return [
                {
                    "event_id": str(r["event_id"]),
                    "memory_id": str(r["memory_id"]),
                    "event_type": str(r["event_type"]),
                    "payload": _load_json(str(r["payload"] or "{}")),
                    "created_at": str(r["created_at"]),
                }
                for r in rows
            ]

    def heatmap(self, bucket_days: int = 7) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    COALESCE(substr(created_at, 1, 10), '') as day,
                    state,
                    COUNT(*) as count,
                    AVG(reinforcement) as avg_reinforcement,
                    AVG(decay_score) as avg_decay
                FROM memory_nodes
                GROUP BY day, state
                ORDER BY day DESC
                """
            ).fetchall()
            return [
                {
                    "day": str(r["day"]),
                    "state": str(r["state"]),
                    "count": int(r["count"] or 0),
                    "avg_reinforcement": round(float(r["avg_reinforcement"] or 0.0), 6),
                    "avg_decay": round(float(r["avg_decay"] or 0.0), 6),
                    "bucket_days": int(bucket_days),
                }
                for r in rows
            ]

    def reinforcement_graph(self, limit: int = 300) -> dict[str, Any]:
        with self._connect() as conn:
            nodes = conn.execute(
                "SELECT memory_id, state, reinforcement, decay_score, importance_score FROM memory_nodes ORDER BY updated_at DESC LIMIT ?",
                (int(limit),),
            ).fetchall()
            edges = conn.execute(
                "SELECT edge_id, from_memory_id, to_memory_id, relation, confidence FROM memory_edges ORDER BY created_at DESC LIMIT ?",
                (int(limit),),
            ).fetchall()
        return {
            "nodes": [
                {
                    "id": str(r["memory_id"]),
                    "state": str(r["state"]),
                    "reinforcement": float(r["reinforcement"] or 0.0),
                    "decay_score": float(r["decay_score"] or 0.0),
                    "importance_score": float(r["importance_score"] or 0.0),
                }
                for r in nodes
            ],
            "edges": [
                {
                    "id": str(r["edge_id"]),
                    "from": str(r["from_memory_id"]),
                    "to": str(r["to_memory_id"]),
                    "relation": str(r["relation"]),
                    "confidence": float(r["confidence"] or 0.0),
                }
                for r in edges
            ],
        }

    def aging(self, limit: int = 200) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT memory_id, state, decay_score, reinforcement, importance_score, last_accessed_at, forgotten_at, updated_at
                FROM memory_nodes
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (int(limit),),
            ).fetchall()
            return [
                {
                    "memory_id": str(r["memory_id"]),
                    "state": str(r["state"]),
                    "decay_score": round(float(r["decay_score"] or 0.0), 6),
                    "reinforcement": round(float(r["reinforcement"] or 0.0), 6),
                    "importance_score": round(float(r["importance_score"] or 0.0), 6),
                    "last_accessed_at": r["last_accessed_at"],
                    "forgotten_at": r["forgotten_at"],
                    "updated_at": r["updated_at"],
                    "next_action": _next_action(float(r["decay_score"] or 0.0), str(r["state"])),
                }
                for r in rows
            ]


def _clip(text: str, size: int) -> str:
    clean = " ".join((text or "").split())
    if len(clean) <= size:
        return clean
    return clean[: max(0, size - 3)].rstrip() + "..."


def _load_json(raw: str) -> dict[str, Any]:
    try:
        data = json.loads(raw or "{}")
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _memory_type(item: dict[str, Any]) -> str:
    tags = [str(v).lower() for v in (item.get("tags") or [])]
    text = str(item.get("text_content") or "").lower()
    if "task" in tags or "todo" in text:
        return "task"
    if "preference" in tags:
        return "preference"
    if "fact" in tags:
        return "fact"
    if "intent" in tags:
        return "intent"
    return "episode"


def _next_action(decay_score: float, state: str) -> str:
    if state == "forgotten":
        return "purged"
    if decay_score >= 0.97:
        return "forget"
    if decay_score >= 0.85:
        return "archive"
    if decay_score >= 0.45:
        return "review"
    return "retain"
