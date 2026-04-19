"""Vision-RCP Stream Router — Routes process output to subscribed WebSocket clients."""

from __future__ import annotations

import asyncio
import collections
import logging
from typing import Any, Callable, Coroutine

from .models import LogEntry

logger = logging.getLogger("rcp.stream_router")


class StreamRouter:
    """Routes stdout/stderr output from processes to subscribed WebSocket clients.

    Features:
    - Per-process ring buffer for log history (tail support)
    - Multiple client subscriptions per process
    - Backpressure handling with buffer limits
    """

    def __init__(self, buffer_size: int = 10000, max_buffer_bytes: int = 1048576):
        self._buffer_size = buffer_size
        self._max_buffer_bytes = max_buffer_bytes

        # pid → deque of LogEntry (ring buffer)
        self._buffers: dict[int, collections.deque[LogEntry]] = {}

        # pid → set of subscriber callbacks
        self._subscribers: dict[int, set[int]] = {}  # pid → set of connection_ids

        # connection_id → callback function
        self._callbacks: dict[int, Callable[[LogEntry], Coroutine]] = {}

        # Global subscribers (receive all process output)
        self._global_subscribers: set[int] = set()

        # Remote relay callback
        self._relay_callback: Optional[Callable[[LogEntry], Coroutine]] = None

    def set_relay_callback(self, callback: Callable[[LogEntry], Coroutine]) -> None:
        """Set the callback for the remote relay client."""
        self._relay_callback = callback

    def _ensure_buffer(self, pid: int) -> collections.deque[LogEntry]:
        if pid not in self._buffers:
            self._buffers[pid] = collections.deque(maxlen=self._buffer_size)
        return self._buffers[pid]

    async def emit(self, entry: LogEntry) -> None:
        """Route a log entry to all subscribers of that process."""
        # Store in ring buffer
        buf = self._ensure_buffer(entry.pid)
        buf.append(entry)

        # 1. Fan out to local subscribers
        # Get targeted + global subscribers
        subscriber_ids = set()
        if entry.pid in self._subscribers:
            subscriber_ids.update(self._subscribers[entry.pid])
        subscriber_ids.update(self._global_subscribers)

        for conn_id in subscriber_ids:
            callback = self._callbacks.get(conn_id)
            if callback:
                try:
                    await callback(entry)
                except Exception as e:
                    logger.warning("Stream delivery failed for conn %d: %s", conn_id, e)

        # 2. Push to remote relay if set
        if self._relay_callback:
            try:
                await self._relay_callback(entry)
            except Exception as e:
                logger.warning("Relay stream delivery failed: %s", e)

    def subscribe(self, connection_id: int, pid: int,
                  callback: Callable[[LogEntry], Coroutine]) -> None:
        """Subscribe a connection to a specific process output."""
        if pid not in self._subscribers:
            self._subscribers[pid] = set()
        self._subscribers[pid].add(connection_id)
        self._callbacks[connection_id] = callback
        logger.debug("Connection %d subscribed to PID %d", connection_id, pid)

    def subscribe_all(self, connection_id: int,
                      callback: Callable[[LogEntry], Coroutine]) -> None:
        """Subscribe a connection to ALL process output."""
        self._global_subscribers.add(connection_id)
        self._callbacks[connection_id] = callback
        logger.debug("Connection %d subscribed to all processes", connection_id)

    def unsubscribe(self, connection_id: int, pid: int | None = None) -> None:
        """Unsubscribe a connection from a process (or all)."""
        if pid is not None:
            subs = self._subscribers.get(pid)
            if subs:
                subs.discard(connection_id)
        else:
            # Unsubscribe from everything
            for subs in self._subscribers.values():
                subs.discard(connection_id)
            self._global_subscribers.discard(connection_id)
            self._callbacks.pop(connection_id, None)

        logger.debug("Connection %d unsubscribed (pid=%s)", connection_id, pid)

    def get_tail(self, pid: int, lines: int = 100) -> list[dict[str, Any]]:
        """Get the last N lines from a process buffer."""
        buf = self._buffers.get(pid)
        if not buf:
            return []

        tail = list(buf)[-lines:]
        return [entry.to_dict() for entry in tail]

    def clear_buffer(self, pid: int) -> None:
        """Clear the buffer for a process."""
        if pid in self._buffers:
            self._buffers[pid].clear()

    def cleanup(self, pid: int) -> None:
        """Remove all data associated with a process."""
        self._buffers.pop(pid, None)
        self._subscribers.pop(pid, None)
