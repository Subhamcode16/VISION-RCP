"""Vision-RCP Protocol — Message definitions and validation."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    COMMAND = "command"
    RESPONSE = "response"
    STREAM = "stream"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    HANDSHAKE = "handshake"


class CommandType(str, Enum):
    PROCESS_SPAWN = "process.spawn"
    PROCESS_KILL = "process.kill"
    PROCESS_RESTART = "process.restart"
    PROCESS_LIST = "process.list"
    PROCESS_STATUS = "process.status"
    PROCESS_LOGS = "process.logs"
    GRAPH_START = "graph.start"
    GRAPH_STOP = "graph.stop"
    GRAPH_STATUS = "graph.status"
    AUTH_LOGIN = "auth.login"
    AUTH_REFRESH = "auth.refresh"
    AUTH_LOGOUT = "auth.logout"
    SYSTEM_INFO = "system.info"
    SYSTEM_PING = "system.ping"
    
    # Audit Logs
    AUDIT_QUERY = "audit.query"

    # Agent Commands
    AGENT_START = "agent.start"
    AGENT_SEND = "agent.send"
    AGENT_INTERRUPT = "agent.interrupt"
    AGENT_STOP = "agent.stop"
    AGENT_APPROVE = "agent.approve"
    SESSION_INFO = "session.info"
    SESSION_LIST_CLIENTS = "session.clients"


class ProcessState(str, Enum):
    PENDING = "pending"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
    RESTARTING = "restarting"


class StreamType(str, Enum):
    STDOUT = "stdout"
    STDERR = "stderr"
    SYSTEM = "system"


class RCPError(BaseModel):
    code: str
    message: str
    details: Optional[dict[str, Any]] = None


class Envelope(BaseModel):
    """RCP protocol message envelope. Every message conforms to this shape."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: MessageType
    ts: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    token: Optional[str] = None
    command: Optional[CommandType] = None
    ref: Optional[str] = None
    payload: Optional[dict[str, Any]] = None
    error: Optional[RCPError] = None

    @classmethod
    def cmd(cls, command: CommandType, payload: dict[str, Any] | None = None,
            token: str | None = None) -> "Envelope":
        return cls(type=MessageType.COMMAND, command=command,
                   payload=payload or {}, token=token)

    @classmethod
    def ok(cls, ref: str, payload: dict[str, Any] | None = None) -> "Envelope":
        return cls(type=MessageType.RESPONSE, ref=ref, payload=payload or {})

    @classmethod
    def err(cls, ref: str, code: str, message: str,
            details: dict[str, Any] | None = None) -> "Envelope":
        return cls(type=MessageType.ERROR, ref=ref,
                   error=RCPError(code=code, message=message, details=details))

    @classmethod
    def stream_msg(cls, ref: str, payload: dict[str, Any]) -> "Envelope":
        return cls(type=MessageType.STREAM, ref=ref, payload=payload)

    @classmethod
    def heartbeat(cls) -> "Envelope":
        return cls(type=MessageType.HEARTBEAT)

    def to_json(self) -> str:
        return self.model_dump_json(exclude_none=True)

    @classmethod
    def from_json(cls, data: str) -> "Envelope":
        return cls.model_validate_json(data)
