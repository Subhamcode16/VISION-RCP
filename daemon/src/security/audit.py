"""Vision-RCP Audit — SQLite-backed audit logger for all security events."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Optional

import aiosqlite

logger = logging.getLogger("rcp.audit")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    event_type TEXT NOT NULL,
    source_ip TEXT,
    command TEXT,
    result TEXT,
    details TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_type ON audit_log(event_type);
"""


class AuditLogger:
    """Persistent audit log stored in SQLite."""

    def __init__(self, data_dir: Path, enabled: bool = True,
                 max_entries: int = 100000, retention_days: int = 30):
        self._db_path = data_dir / "audit.db"
        self._enabled = enabled
        self._max_entries = max_entries
        self._retention_days = retention_days
        self._db: Optional[aiosqlite.Connection] = None

    async def initialize(self) -> None:
        if not self._enabled:
            return
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(str(self._db_path))
        await self._db.executescript(_SCHEMA)
        await self._db.commit()
        logger.info("Audit log initialized at %s", self._db_path)

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    async def log(self, event_type: str, source_ip: str = "",
                  command: str = "", result: str = "",
                  details: str = "") -> None:
        """Write an audit entry."""
        if not self._enabled or not self._db:
            return

        try:
            await self._db.execute(
                "INSERT INTO audit_log (timestamp, event_type, source_ip, command, result, details) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (time.time(), event_type, source_ip, command, result, details),
            )
            await self._db.commit()
        except Exception as e:
            logger.error("Failed to write audit log: %s", e)

    async def log_auth_attempt(self, source_ip: str, success: bool) -> None:
        await self.log(
            event_type="auth.attempt",
            source_ip=source_ip,
            result="success" if success else "failure",
        )

    async def log_command(self, source_ip: str, command: str,
                          result: str = "ok", details: str = "") -> None:
        await self.log(
            event_type="command",
            source_ip=source_ip,
            command=command,
            result=result,
            details=details,
        )

    async def log_process_event(self, event: str, details: str = "") -> None:
        await self.log(
            event_type=f"process.{event}",
            details=details,
        )

    async def log_security_event(self, event: str, source_ip: str = "",
                                  details: str = "") -> None:
        await self.log(
            event_type=f"security.{event}",
            source_ip=source_ip,
            details=details,
        )

    async def query(self, since: Optional[float] = None,
                    until: Optional[float] = None,
                    event_type: Optional[str] = None,
                    limit: int = 100) -> list[dict[str, Any]]:
        """Query audit log entries."""
        if not self._db:
            return []

        conditions = []
        params: list[Any] = []

        if since is not None:
            conditions.append("timestamp >= ?")
            params.append(since)
        if until is not None:
            conditions.append("timestamp <= ?")
            params.append(until)
        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"SELECT * FROM audit_log {where} ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        rows = []
        async with self._db.execute(query, params) as cursor:
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            async for row in cursor:
                rows.append(dict(zip(columns, row)))

        return rows

    async def cleanup(self) -> None:
        """Remove old entries beyond retention period."""
        if not self._db:
            return

        cutoff = time.time() - (self._retention_days * 86400)
        await self._db.execute("DELETE FROM audit_log WHERE timestamp < ?", (cutoff,))
        await self._db.commit()
        logger.info("Audit log cleanup: removed entries older than %d days", self._retention_days)
