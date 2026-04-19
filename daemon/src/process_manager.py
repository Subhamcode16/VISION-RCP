"""Vision-RCP Process Manager — Full lifecycle management for local processes."""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
import time
from typing import Any, Callable, Coroutine, Optional



from .models import LogEntry, ManagedProcess
from .protocol import ProcessState
from .stream_router import StreamRouter

logger = logging.getLogger("rcp.process_manager")


class ProcessManager:
    """Manages the lifecycle of local processes: spawn, monitor, kill, restart."""

    def __init__(self, stream_router: StreamRouter,
                 default_auto_restart: bool = False,
                 default_max_restarts: int = 5,
                 health_check_interval: float = 5.0):
        self._processes: dict[int, ManagedProcess] = {}  # pid → process
        self._by_name: dict[str, ManagedProcess] = {}    # name → process
        self._stream_router = stream_router
        self._default_auto_restart = default_auto_restart
        self._default_max_restarts = default_max_restarts
        self._health_check_interval = health_check_interval
        self._health_task: Optional[asyncio.Task] = None
        self._on_state_change: Optional[Callable[[ManagedProcess], Coroutine]] = None

    def set_state_callback(self, callback: Callable[[ManagedProcess], Coroutine]) -> None:
        """Register a callback for process state changes."""
        self._on_state_change = callback

    async def _notify_state_change(self, proc: ManagedProcess) -> None:
        if self._on_state_change:
            try:
                await self._on_state_change(proc)
            except Exception as e:
                logger.error("State change callback failed: %s", e)

    async def spawn(self, name: str, cmd: str, args: list[str] | None = None,
                    env: dict[str, str] | None = None, cwd: str | None = None,
                    depends_on: list[str] | None = None,
                    auto_restart: bool | None = None,
                    max_restarts: int | None = None,
                    group: str | None = None) -> ManagedProcess:
        """Spawn a new managed process."""
        if name in self._by_name:
            existing = self._by_name[name]
            if existing.state == ProcessState.RUNNING:
                raise ValueError(f"Process '{name}' is already running (PID {existing.pid})")

        proc = ManagedProcess(
            name=name,
            cmd=cmd,
            args=args or [],
            env=env or {},
            cwd=cwd,
            depends_on=depends_on or [],
            auto_restart=auto_restart if auto_restart is not None else self._default_auto_restart,
            max_restarts=max_restarts if max_restarts is not None else self._default_max_restarts,
            group=group,
        )

        await self._start_process(proc)
        return proc

    async def _start_process(self, proc: ManagedProcess) -> None:
        """Actually start the OS process."""
        proc.state = ProcessState.STARTING
        await self._notify_state_change(proc)

        try:
            full_env = {**os.environ, **proc.env}

            # Build command
            cmd_parts = [proc.cmd] + proc.args

            # Platform-specific flags
            kwargs: dict[str, Any] = {
                "stdout": asyncio.subprocess.PIPE,
                "stderr": asyncio.subprocess.PIPE,
                "env": full_env,
            }

            if proc.cwd:
                kwargs["cwd"] = proc.cwd

            if sys.platform == "win32":
                kwargs["creationflags"] = (
                    0x00000200  # CREATE_NEW_PROCESS_GROUP
                    | 0x00000008  # DETACHED_PROCESS
                )

            process = await asyncio.create_subprocess_exec(
                *cmd_parts, **kwargs
            )

            proc._process = process
            proc.pid = process.pid
            proc.state = ProcessState.RUNNING
            proc.started_at = time.time()
            proc.exit_code = None

            # Register in lookups
            self._processes[proc.pid] = proc
            self._by_name[proc.name] = proc

            # Start stream readers
            proc._stdout_task = asyncio.create_task(
                self._read_stream(proc, process.stdout, "stdout")
            )
            proc._stderr_task = asyncio.create_task(
                self._read_stream(proc, process.stderr, "stderr")
            )

            # Start exit watcher
            asyncio.create_task(self._watch_exit(proc))

            await self._notify_state_change(proc)
            logger.info("Spawned process '%s' (PID %d): %s",
                        proc.name, proc.pid, " ".join(cmd_parts))

        except Exception as e:
            proc.state = ProcessState.FAILED
            await self._notify_state_change(proc)
            logger.error("Failed to spawn '%s': %s", proc.name, e)
            raise

    async def _read_stream(self, proc: ManagedProcess,
                           stream: asyncio.StreamReader | None,
                           stream_type: str) -> None:
        """Read from stdout/stderr and route to stream router."""
        if not stream:
            return

        try:
            while True:
                line = await stream.readline()
                if not line:
                    break

                text = line.decode("utf-8", errors="replace").rstrip("\n\r")
                if text:
                    entry = LogEntry(
                        pid=proc.pid or 0,
                        name=proc.name,
                        stream=stream_type,
                        data=text,
                    )
                    await self._stream_router.emit(entry)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("Stream reader error for '%s' (%s): %s",
                         proc.name, stream_type, e)

    async def _watch_exit(self, proc: ManagedProcess) -> None:
        """Watch for process exit and handle auto-restart."""
        if not proc._process:
            return

        try:
            exit_code = await proc._process.wait()
            proc.exit_code = exit_code

            # Clean up from pid registry
            if proc.pid and proc.pid in self._processes:
                del self._processes[proc.pid]

            if exit_code == 0:
                proc.state = ProcessState.STOPPED
                logger.info("Process '%s' (PID %d) exited cleanly",
                            proc.name, proc.pid)
            else:
                proc.state = ProcessState.FAILED
                logger.warning("Process '%s' (PID %d) exited with code %d",
                               proc.name, proc.pid, exit_code)

                # Auto-restart logic
                if proc.auto_restart and proc.restart_count < proc.max_restarts:
                    proc.restart_count += 1
                    delay = min(2 ** proc.restart_count, 60)
                    proc.state = ProcessState.RESTARTING
                    await self._notify_state_change(proc)

                    logger.info("Restarting '%s' in %ds (attempt %d/%d)",
                                proc.name, delay, proc.restart_count, proc.max_restarts)

                    await asyncio.sleep(delay)
                    await self._start_process(proc)
                    return

            await self._notify_state_change(proc)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("Exit watcher error for '%s': %s", proc.name, e)

    async def kill(self, pid: int, sig: str = "SIGTERM") -> bool:
        """Kill a process by PID."""
        proc = self._processes.get(pid)
        if not proc:
            # Try by name lookup via pid
            for p in self._by_name.values():
                if p.pid == pid:
                    proc = p
                    break

        if not proc or not proc._process:
            logger.warning("Cannot kill PID %d: not found", pid)
            return False

        proc.state = ProcessState.STOPPING
        proc.auto_restart = False  # Disable auto-restart on manual kill
        await self._notify_state_change(proc)

        try:
            if sys.platform == "win32":
                proc._process.terminate()
            else:
                sig_num = getattr(signal, sig, signal.SIGTERM)
                proc._process.send_signal(sig_num)

            # Cancel stream readers
            if proc._stdout_task:
                proc._stdout_task.cancel()
            if proc._stderr_task:
                proc._stderr_task.cancel()

            logger.info("Sent %s to '%s' (PID %d)", sig, proc.name, pid)
            return True

        except ProcessLookupError:
            proc.state = ProcessState.STOPPED
            await self._notify_state_change(proc)
            return True
        except Exception as e:
            logger.error("Failed to kill PID %d: %s", pid, e)
            return False

    async def restart(self, pid: int) -> Optional[ManagedProcess]:
        """Restart a process by PID."""
        proc = self._processes.get(pid)
        if not proc:
            for p in self._by_name.values():
                if p.pid == pid:
                    proc = p
                    break

        if not proc:
            return None

        await self.kill(pid)

        # Wait for process to actually exit
        if proc._process:
            try:
                await asyncio.wait_for(proc._process.wait(), timeout=10)
            except asyncio.TimeoutError:
                if proc._process:
                    proc._process.kill()

        proc.restart_count += 1
        await self._start_process(proc)
        return proc

    def get_process(self, pid: int) -> Optional[ManagedProcess]:
        """Get process info by PID."""
        return self._processes.get(pid)

    def get_by_name(self, name: str) -> Optional[ManagedProcess]:
        """Get process by name."""
        return self._by_name.get(name)

    def list_processes(self) -> list[dict[str, Any]]:
        """List all managed processes with live metrics."""
        result = []
        for proc in self._by_name.values():
            info = proc.to_dict()

            # Enrich with live psutil metrics if running
            if proc.pid and proc.state == ProcessState.RUNNING:
                try:
                    import psutil
                    ps = psutil.Process(proc.pid)
                    info["cpu_percent"] = ps.cpu_percent(interval=0)
                    mem = ps.memory_info()
                    info["memory_rss"] = mem.rss
                    info["memory_vms"] = mem.vms
                except (Exception, ImportError):
                    info["cpu_percent"] = 0.0
                    info["memory_rss"] = 0
                    info["memory_vms"] = 0
            else:
                info["cpu_percent"] = 0.0
                info["memory_rss"] = 0
                info["memory_vms"] = 0

            result.append(info)
        return result

    def get_status(self, pid: int) -> Optional[dict[str, Any]]:
        """Get detailed status for a single process."""
        proc = self._processes.get(pid)
        if not proc:
            return None

        info = proc.to_dict()
        if proc.state == ProcessState.RUNNING:
            try:
                import psutil
                ps = psutil.Process(pid)
                info["cpu_percent"] = ps.cpu_percent(interval=0.1)
                mem = ps.memory_info()
                info["memory_rss"] = mem.rss
                info["memory_vms"] = mem.vms
                info["num_threads"] = ps.num_threads()
                info["connections"] = len(ps.net_connections())
            except (Exception, ImportError):
                pass

        return info

    async def start_health_monitor(self) -> None:
        """Start periodic health checking of all processes."""
        self._health_task = asyncio.create_task(self._health_loop())

    async def _health_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(self._health_check_interval)
                for proc in list(self._by_name.values()):
                    if proc.state != ProcessState.RUNNING or not proc.pid:
                        continue
                    try:
                        import psutil
                        ps = psutil.Process(proc.pid)
                        if not ps.is_running():
                            proc.state = ProcessState.FAILED
                            await self._notify_state_change(proc)
                    except (Exception, ImportError):
                        pass
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Health check error: %s", e)

    async def shutdown(self) -> None:
        """Gracefully stop all managed processes."""
        if self._health_task:
            self._health_task.cancel()

        for proc in list(self._by_name.values()):
            if proc.state == ProcessState.RUNNING and proc.pid:
                await self.kill(proc.pid)

        # Wait for all to exit
        for proc in list(self._by_name.values()):
            if proc._process:
                try:
                    await asyncio.wait_for(proc._process.wait(), timeout=5)
                except asyncio.TimeoutError:
                    if proc._process:
                        proc._process.kill()

        logger.info("All managed processes stopped")
