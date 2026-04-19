"""Vision-RCP Models — Data structures for processes, groups, and system info."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional

from .protocol import ProcessState


@dataclass
class ManagedProcess:
    """Represents a process managed by the daemon."""
    name: str
    cmd: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    cwd: Optional[str] = None
    depends_on: list[str] = field(default_factory=list)
    auto_restart: bool = False
    max_restarts: int = 5
    group: Optional[str] = None

    # Runtime state
    pid: Optional[int] = None
    state: ProcessState = ProcessState.PENDING
    started_at: Optional[float] = None
    restart_count: int = 0
    exit_code: Optional[int] = None

    # Internal references (not serialized)
    _process: Any = field(default=None, repr=False)
    _stdout_task: Any = field(default=None, repr=False)
    _stderr_task: Any = field(default=None, repr=False)

    @property
    def uptime(self) -> float:
        if self.started_at and self.state == ProcessState.RUNNING:
            return time.time() - self.started_at
        return 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "cmd": self.cmd,
            "args": self.args,
            "cwd": self.cwd,
            "depends_on": self.depends_on,
            "auto_restart": self.auto_restart,
            "group": self.group,
            "pid": self.pid,
            "state": self.state.value,
            "started_at": self.started_at,
            "restart_count": self.restart_count,
            "exit_code": self.exit_code,
            "uptime": round(self.uptime, 1),
        }


@dataclass
class ProcessGroup:
    """A named group of processes with dependency relationships."""
    name: str
    processes: dict[str, ManagedProcess] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "processes": {k: v.to_dict() for k, v in self.processes.items()},
        }


@dataclass
class SystemInfo:
    """Snapshot of system metrics."""
    os: str = ""
    platform: str = ""
    hostname: str = ""
    cpu_count: int = 0
    cpu_percent: float = 0.0
    memory_total: int = 0
    memory_used: int = 0
    memory_percent: float = 0.0
    disk_total: int = 0
    disk_used: int = 0
    disk_percent: float = 0.0
    uptime: float = 0.0
    daemon_port: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "os": self.os,
            "platform": self.platform,
            "hostname": self.hostname,
            "cpu_count": self.cpu_count,
            "cpu_percent": self.cpu_percent,
            "memory_total": self.memory_total,
            "memory_used": self.memory_used,
            "memory_percent": self.memory_percent,
            "disk_total": self.disk_total,
            "disk_used": self.disk_used,
            "disk_percent": self.disk_percent,
            "uptime": round(self.uptime, 1),
            "daemon_port": self.daemon_port,
        }


@dataclass
class LogEntry:
    """A single line of process output."""
    pid: int
    name: str
    stream: str  # stdout | stderr | system
    data: str
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pid": self.pid,
            "name": self.name,
            "stream": self.stream,
            "data": self.data,
            "ts": self.ts,
        }
