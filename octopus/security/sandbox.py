"""Sandbox queue — actions are staged here before any side effects occur."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Generator

from octopus.config import load_config
from octopus.models import ActionType, SandboxAction


class ActionSandbox:
    """Persistent SQLite-backed queue for staged actions awaiting approval."""

    def __init__(self, db_path: str | None = None) -> None:
        path = Path(db_path or load_config().sandbox.db_path).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = str(path)
        self._init_db()

    @contextmanager
    def _conn(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sandbox_actions (
                    id TEXT PRIMARY KEY,
                    action_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    workflow_id TEXT NOT NULL,
                    workflow_name TEXT NOT NULL,
                    triggered_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    approved INTEGER,
                    executed_at TEXT
                )
            """)

    def stage(self, action: SandboxAction) -> None:
        """Deposit an action into the sandbox for later approval."""
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO sandbox_actions
                   (id, action_type, payload, workflow_id, workflow_name,
                    triggered_by, created_at, approved, executed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    action.id,
                    action.action_type.value,
                    json.dumps(action.payload),
                    action.workflow_id,
                    action.workflow_name,
                    action.triggered_by,
                    action.created_at.isoformat(),
                    None,
                    None,
                ),
            )

    def pending(self, workflow_id: str | None = None) -> list[SandboxAction]:
        """Return all actions awaiting a decision."""
        with self._conn() as conn:
            if workflow_id:
                rows = conn.execute(
                    "SELECT * FROM sandbox_actions WHERE approved IS NULL AND workflow_id = ?",
                    (workflow_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM sandbox_actions WHERE approved IS NULL"
                ).fetchall()
        return [self._row_to_action(r) for r in rows]

    def all_pending_by_workflow(self) -> dict[str, list[SandboxAction]]:
        """Return pending actions grouped by workflow_id."""
        grouped: dict[str, list[SandboxAction]] = {}
        for action in self.pending():
            grouped.setdefault(action.workflow_id, []).append(action)
        return grouped

    def approve(self, action_id: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE sandbox_actions SET approved = 1, executed_at = ? WHERE id = ?",
                (datetime.utcnow().isoformat(), action_id),
            )

    def reject(self, action_id: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE sandbox_actions SET approved = 0, executed_at = ? WHERE id = ?",
                (datetime.utcnow().isoformat(), action_id),
            )

    def approve_workflow(self, workflow_id: str) -> None:
        for action in self.pending(workflow_id):
            self.approve(action.id)

    def reject_workflow(self, workflow_id: str) -> None:
        for action in self.pending(workflow_id):
            self.reject(action.id)

    def expire_old(self) -> int:
        """Remove actions older than the configured TTL. Returns count removed."""
        hours = load_config().sandbox.auto_expire_hours
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        with self._conn() as conn:
            cur = conn.execute(
                "DELETE FROM sandbox_actions WHERE approved IS NULL AND created_at < ?",
                (cutoff,),
            )
            return cur.rowcount

    @staticmethod
    def _row_to_action(row: sqlite3.Row) -> SandboxAction:
        return SandboxAction(
            id=row["id"],
            action_type=ActionType(row["action_type"]),
            payload=json.loads(row["payload"]),
            workflow_id=row["workflow_id"],
            workflow_name=row["workflow_name"],
            triggered_by=row["triggered_by"],
            created_at=datetime.fromisoformat(row["created_at"]),
            approved=bool(row["approved"]) if row["approved"] is not None else None,
            executed_at=datetime.fromisoformat(row["executed_at"]) if row["executed_at"] else None,
        )
