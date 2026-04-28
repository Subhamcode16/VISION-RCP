"""Base abstract class for Vision-RCP Agent Adapters."""

import abc
from typing import AsyncGenerator, Optional, Dict, Any, Callable, Coroutine
from ..models import LogEntry
import time

class AgentAdapter(abc.ABC):
    """Abstract base class for wrapping an underlying agent (like Antigravity, Claude, etc)."""
    
    def __init__(self, name: str, emit_callback: Callable[[LogEntry], Coroutine]):
        self.name = name
        self.emit_callback = emit_callback
        self.is_running = False

    @abc.abstractmethod
    async def start(self, config: Dict[str, Any]) -> None:
        """Initialize the agent process or session."""
        pass

    @abc.abstractmethod
    async def send_message(self, message: str) -> None:
        """Send a natural language prompt to the agent."""
        pass

    @abc.abstractmethod
    async def stream_output(self) -> None:
        """Stream the agent's output back to Vision-RCP via emit_callback."""
        pass

    @abc.abstractmethod
    async def interrupt(self) -> None:
        """Signal the agent to halt its current operation."""
        pass

    @abc.abstractmethod
    async def stop(self) -> None:
        """Gracefully terminate the agent."""
        pass

    @abc.abstractmethod
    async def send_approval(self, decision: bool) -> None:
        """Send an approval decision to the agent if it is waiting."""
        pass

    async def emit_message(self, content: str) -> None:
        """Helper to emit an AGENT_MESSAGE log entry."""
        # Stage 25: Critical Bridge Log
        # This confirms that the message has been captured and is ready for the relay.
        ts = time.time()
        print(f" [BRIDGE] -> AGENT_MESSAGE: '{content[:100]}...' (len: {len(content)})")
        
        entry = LogEntry(
            pid=-1,  # Agent adapters might not have a traditional PID
            name=self.name,
            stream="agent_message",
            data=content,
            ts=ts
        )
        await self.emit_callback(entry)

    async def emit_diagnostic(self, content: str) -> None:
        """Helper to emit an internal log entry (visible in Terminal, not Chat)."""
        entry = LogEntry(
            pid=0,  # PID 0 designates system/adapter diagnostics
            name=self.name,
            stream="stdout",
            data=f"[ADAPTER] {content}",
            ts=time.time()
        )
        await self.emit_callback(entry)

    async def emit_approval_request(self, content: str) -> None:
        """Helper to emit an APPROVAL_REQUEST log entry."""
        entry = LogEntry(
            pid=-1,
            name=self.name,
            stream="approval_request",
            data=content,
            ts=time.time()
        )
        await self.emit_callback(entry)

    @property
    def pid(self) -> Optional[int]:
        """Return the process ID of the agent, if applicable."""
        return None
