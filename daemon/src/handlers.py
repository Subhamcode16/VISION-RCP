"""Vision-RCP Handlers — Command routing and execution."""

from __future__ import annotations

import asyncio
import logging
import os
import platform
import socket
import time
from typing import Any, Callable, Optional


from .config import Config
from .dependency_graph import DependencyGraphEngine
from .models import LogEntry, SystemInfo
from .process_manager import ProcessManager
from .protocol import CommandType, Envelope
from .security.audit import AuditLogger
from pathlib import Path

from .security.auth import AuthManager
from .security.rate_limiter import RateLimiter
from .stream_router import StreamRouter
from .adapters import AdapterRegistry, AgentAdapter

logger = logging.getLogger("rcp.handlers")

_DAEMON_START_TIME = time.time()


class CommandHandler:
    """Routes incoming RCP commands to the appropriate action."""

    def __init__(self, config: Config, auth: AuthManager,
                 process_manager: ProcessManager,
                 dep_graph: DependencyGraphEngine,
                 stream_router: StreamRouter,
                 audit: AuditLogger,
                 rate_limiter: RateLimiter,
                 daemon_port: int,
                 session_provider: Optional[Callable[[], dict]] = None):
        self._config = config
        self._auth = auth
        self._pm = process_manager
        self._dg = dep_graph
        self._sr = stream_router
        self._audit = audit
        self._rl = rate_limiter
        self._daemon_port = daemon_port
        self._session_provider = session_provider
        self._active_adapters: dict[str, AgentAdapter] = {}
        # Deduplication cache for AGENT_SEND to prevent bursts
        self._guard_cache: dict[str, float] = {}

    # Commands that do NOT require auth
    _AUTH_EXEMPT = {CommandType.AUTH_LOGIN, CommandType.SYSTEM_PING, CommandType.SESSION_INFO}

    async def handle(self, envelope: Envelope, connection_id: int | str,
                     source_ip: str) -> Envelope:
        """Process a command envelope and return a response."""
        if not envelope.command:
            return Envelope.err(envelope.id, "INVALID_COMMAND",
                                "Missing command field")

        # Rate limiting
        if envelope.command == CommandType.AUTH_LOGIN:
            if not self._rl.check_auth(source_ip):
                await self._audit.log_security_event("rate_limit", source_ip,
                                                      f"auth rate limit hit")
                return Envelope.err(envelope.id, "RATE_LIMITED",
                                    "Too many auth attempts. Try again later.")
        else:
            if not self._rl.check_command(str(connection_id)):
                await self._audit.log_security_event("rate_limit", source_ip,
                                                      "command rate limit hit")
                return Envelope.err(envelope.id, "RATE_LIMITED",
                                    "Rate limit exceeded. Slow down.")

        # Auth check (skip for exempt commands)
        if envelope.command not in self._AUTH_EXEMPT:
            if not envelope.token:
                return Envelope.err(envelope.id, "AUTH_REQUIRED",
                                    "Authentication required")
            claims = self._auth.validate_token(envelope.token)
            if not claims:
                await self._audit.log_security_event("invalid_token", source_ip)
                return Envelope.err(envelope.id, "AUTH_INVALID",
                                    "Invalid or expired token")

        # Route to handler
        handler_map = {
            CommandType.AUTH_LOGIN: self._handle_auth_login,
            CommandType.AUTH_REFRESH: self._handle_auth_refresh,
            CommandType.AUTH_LOGOUT: self._handle_auth_logout,
            CommandType.PROCESS_SPAWN: self._handle_process_spawn,
            CommandType.PROCESS_KILL: self._handle_process_kill,
            CommandType.PROCESS_RESTART: self._handle_process_restart,
            CommandType.PROCESS_LIST: self._handle_process_list,
            CommandType.PROCESS_STATUS: self._handle_process_status,
            CommandType.PROCESS_LOGS: self._handle_process_logs,
            CommandType.GRAPH_START: self._handle_graph_start,
            CommandType.GRAPH_STOP: self._handle_graph_stop,
            CommandType.GRAPH_STATUS: self._handle_graph_status,
            CommandType.SYSTEM_INFO: self._handle_system_info,
            CommandType.SYSTEM_PING: self._handle_system_ping,
            CommandType.AUDIT_QUERY: self._handle_audit_query,
            CommandType.SESSION_INFO: self._handle_session_info,
            CommandType.AGENT_START: self._handle_agent_start,
            CommandType.AGENT_SEND: self._handle_agent_send,
            CommandType.AGENT_INTERRUPT: self._handle_agent_interrupt,
            CommandType.AGENT_STOP: self._handle_agent_stop,
            CommandType.AGENT_APPROVE: self._handle_agent_approve,
        }

        handler = handler_map.get(envelope.command)
        if not handler:
            return Envelope.err(envelope.id, "UNKNOWN_COMMAND",
                                f"Unknown command: {envelope.command}")

        try:
            result = await handler(envelope.payload or {}, connection_id, source_ip)
            await self._audit.log_command(source_ip, envelope.command.value, "ok")
            return Envelope.ok(envelope.id, result)
        except Exception as e:
            logger.error("Handler error for %s: %s", envelope.command, e)
            await self._audit.log_command(source_ip, envelope.command.value,
                                          "error", str(e))
            return Envelope.err(envelope.id, "INTERNAL_ERROR", str(e))

    # ─── Auth Handlers ──────────────────────────────────────────

    async def _handle_auth_login(self, payload: dict, conn_id: int,
                                  source_ip: str) -> dict[str, Any]:
        secret = payload.get("secret", "")
        result = self._auth.login(secret)
        if not result:
            await self._audit.log_auth_attempt(source_ip, False)
            raise PermissionError("Invalid secret key")

        await self._audit.log_auth_attempt(source_ip, True)
        return result

    async def _handle_auth_refresh(self, payload: dict, conn_id: int,
                                    source_ip: str) -> dict[str, Any]:
        token = payload.get("refresh_token", "")
        result = self._auth.refresh(token)
        if not result:
            raise PermissionError("Invalid or expired refresh token")
        return result

    async def _handle_auth_logout(self, payload: dict, conn_id: int,
                                   source_ip: str) -> dict[str, Any]:
        token = payload.get("token", "")
        self._auth.revoke_token(token)
        return {"success": True}

    # ─── Process Handlers ───────────────────────────────────────

    async def _handle_process_spawn(self, payload: dict, conn_id: int,
                                     source_ip: str) -> dict[str, Any]:
        proc = await self._pm.spawn(
            name=payload["name"],
            cmd=payload["cmd"],
            args=payload.get("args", []),
            env=payload.get("env", {}),
            cwd=payload.get("cwd"),
            depends_on=payload.get("depends_on", []),
            auto_restart=payload.get("auto_restart", False),
            max_restarts=payload.get("max_restarts", 5),
            group=payload.get("group"),
        )
        await self._audit.log_process_event("spawn",
                                             f"{proc.name} PID={proc.pid}")
        return {"pid": proc.pid, "name": proc.name, "state": proc.state.value}

    async def _handle_process_kill(self, payload: dict, conn_id: int,
                                    source_ip: str) -> dict[str, Any]:
        pid = payload["pid"]
        sig = payload.get("signal", "SIGTERM")
        success = await self._pm.kill(pid, sig)
        await self._audit.log_process_event("kill", f"PID={pid} signal={sig}")
        return {"success": success, "pid": pid}

    async def _handle_process_restart(self, payload: dict, conn_id: int,
                                       source_ip: str) -> dict[str, Any]:
        pid = payload["pid"]
        proc = await self._pm.restart(pid)
        if not proc:
            raise ValueError(f"Process with PID {pid} not found")
        await self._audit.log_process_event("restart",
                                             f"{proc.name} new PID={proc.pid}")
        return {"pid": proc.pid, "name": proc.name, "state": proc.state.value}

    async def _handle_process_list(self, payload: dict, conn_id: int,
                                    source_ip: str) -> dict[str, Any]:
        return {"processes": self._pm.list_processes()}

    async def _handle_process_status(self, payload: dict, conn_id: int,
                                      source_ip: str) -> dict[str, Any]:
        pid = payload["pid"]
        status = self._pm.get_status(pid)
        if not status:
            raise ValueError(f"Process with PID {pid} not found")
        return status

    async def _handle_process_logs(self, payload: dict, conn_id: int,
                                    source_ip: str) -> dict[str, Any]:
        pid = payload["pid"]
        tail = payload.get("tail", 100)
        lines = self._sr.get_tail(pid, tail)
        return {"pid": pid, "lines": lines, "count": len(lines)}

    # ─── Graph Handlers ─────────────────────────────────────────

    async def _handle_graph_start(self, payload: dict, conn_id: int,
                                   source_ip: str) -> dict[str, Any]:
        group = payload["group"]
        results = await self._dg.start_group(group)
        await self._audit.log_process_event("graph.start",
                                             f"group={group} count={len(results)}")
        return {"group": group, "results": results}

    async def _handle_graph_stop(self, payload: dict, conn_id: int,
                                  source_ip: str) -> dict[str, Any]:
        group = payload["group"]
        results = await self._dg.stop_group(group)
        await self._audit.log_process_event("graph.stop", f"group={group}")
        return {"group": group, "results": results}

    async def _handle_graph_status(self, payload: dict, conn_id: int,
                                    source_ip: str) -> dict[str, Any]:
        return {"graphs": self._dg.get_graph_status()}

    # ─── System Handlers ────────────────────────────────────────

    async def _handle_system_info(self, payload: dict, conn_id: int,
                                   source_ip: str) -> dict[str, Any]:
        import psutil
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        
        # Defensive platform info to avoid WMI crashes
        os_name = "Windows" if os.name == "nt" else "Unix"
        platform_str = "Unknown"
        hostname = "Unknown"
        
        try:
            platform_str = platform.platform()
            hostname = socket.gethostname()
        except Exception:
            pass

        info = SystemInfo(
            os=os_name,
            platform=platform_str,
            hostname=hostname,
            cpu_count=psutil.cpu_count() or 0,
            cpu_percent=psutil.cpu_percent(interval=0.1),
            memory_total=mem.total,
            memory_used=mem.used,
            memory_percent=mem.percent,
            disk_total=disk.total,
            disk_used=disk.used,
            disk_percent=disk.percent,
            uptime=time.time() - _DAEMON_START_TIME,
            daemon_port=self._daemon_port,
        )
        return info.to_dict()

    async def _handle_system_ping(self, payload: dict, conn_id: int,
                                   source_ip: str) -> dict[str, Any]:
        return {"pong": True, "ts": time.time()}

    # ─── Audit Handlers ─────────────────────────────────────────

    async def _handle_audit_query(self, payload: dict, conn_id: int,
                                   source_ip: str) -> dict[str, Any]:
        entries = await self._audit.query(
            since=payload.get("since"),
            until=payload.get("until"),
            event_type=payload.get("event_type"),
            limit=payload.get("limit", 100),
        )
        return {"entries": entries, "count": len(entries)}

    def _resolve_adapter(self, name: str) -> AgentAdapter:
        """Resolve an adapter by name, with fallback to the only active one."""
        adapter = self._active_adapters.get(name)
        if adapter:
            return adapter
            
        # Smart Fallback: If only one adapter is running, use it regardless of name
        if len(self._active_adapters) == 1:
            fallback_name = next(iter(self._active_adapters.keys()))
            logger.info("Smart Routing fallback: Mapping requested agent '%s' to active '%s'", 
                        name, fallback_name)
            return self._active_adapters[fallback_name]
            
        raise ValueError(f"Agent '{name}' is not running.")

    # ─── Session Handlers ───────────────────────────────────────

    async def _handle_session_info(self, payload: dict, conn_id: int,
                                    source_ip: str) -> dict[str, Any]:
        info = {}
        if self._session_provider:
            info = self._session_provider()
            
        is_relay = bool(info.get("session_id"))
        
        # Find active agent
        agent_name = None
        agent_status = "idle"
        if self._active_adapters:
            # Just take the first one for now as we usually run one agent per RCP session
            agent_name = next(iter(self._active_adapters.keys()))
            adapter = self._active_adapters[agent_name]
            agent_status = "running" if adapter.is_running else "stopped"

        # List all configured agents
        available_agents = []
        try:
            agents_cfg_path = Path("agents.toml")
            if agents_cfg_path.exists():
                with open(agents_cfg_path, "rb") as f:
                    import sys
                    if sys.version_info >= (3, 11):
                        import tomllib
                    else:
                        try:
                            import tomllib
                        except ImportError:
                            import tomli as tomllib
                    agents_data = tomllib.load(f)
                    available_agents = list(agents_data.keys())
        except Exception:
            pass
            
        return {
            "active": True,
            "session_id": info.get("session_id", "LOCAL"),
            "device_name": info.get("device_name", socket.gethostname()),
            "workspace": str(Path.cwd()),
            "agent_name": agent_name,
            "agent_status": agent_status,
            "available_agents": available_agents,
            "mode": "relay" if is_relay else "local",
            "connected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(_DAEMON_START_TIME)),
        }

    # ─── Agent Handlers ─────────────────────────────────────────

    async def _handle_agent_start(self, payload: dict, conn_id: int, source_ip: str) -> dict[str, Any]:
        name = payload["name"]
        
        # Merge payload config with agents.toml config if it exists
        merged_config = payload.get("config", {})
        try:
            import sys
            if sys.version_info >= (3, 11):
                import tomllib
            else:
                try:
                    import tomllib
                except ImportError:
                    import tomli as tomllib
                    
            agents_cfg_path = Path("agents.toml")
                
            if agents_cfg_path.exists():
                with open(agents_cfg_path, "rb") as f:
                    agents_data = tomllib.load(f)
                    if name in agents_data:
                        merged_config.update(agents_data[name])
        except Exception as e:
            logger.warning(f"Failed to load agents.toml: {e}")

        if name in self._active_adapters:
            return {"status": "already_running"}

        async def emit_callback(entry: LogEntry):
            await self._sr.emit(entry)

        adapter = AdapterRegistry.get(name, emit_callback)
        await adapter.start(merged_config)
        self._active_adapters[name] = adapter

        # Start streaming task
        asyncio.create_task(adapter.stream_output())

        return {"status": "started", "name": name}

    async def _handle_agent_send(self, payload: dict, conn_id: int, source_ip: str) -> dict[str, Any]:
        name = payload.get("name")
        message = payload.get("message", "")

        # Guard against "Burst" duplication (2-3 identical messages in <500ms)
        cache_key = f"{name}:{message}"
        now = time.time()
        if cache_key in self._guard_cache:
            last_time = self._guard_cache[cache_key]
            if now - last_time < 0.5: # 500ms window
                logger.warning(f"CommandGuard: Dropping duplicate AGENT_SEND for {name} (Burst detected)")
                return {"status": "dropped", "reason": "duplicate_burst"}
        
        # Cleanup old cache entries occasionally
        if len(self._guard_cache) > 100:
            self._guard_cache = {k: v for k, v in self._guard_cache.items() if now - v < 5.0}

        self._guard_cache[cache_key] = now

        adapter = self._resolve_adapter(name)
        await adapter.send_message(message)
        return {"status": "sent"}

    async def _handle_agent_interrupt(self, payload: dict, conn_id: int, source_ip: str) -> dict[str, Any]:
        name = payload["name"]
        adapter = self._resolve_adapter(name)
        await adapter.interrupt()
        return {"status": "interrupted"}

    async def _handle_agent_stop(self, payload: dict, conn_id: int, source_ip: str) -> dict[str, Any]:
        name = payload["name"]
        adapter = self._active_adapters.get(name) # Don't fallback for STOP, be explicit
        if not adapter:
            raise ValueError(f"Agent '{name}' is not running.")

        await adapter.stop()
        del self._active_adapters[name]
        return {"status": "stopped"}

    async def _handle_agent_approve(self, payload: dict, conn_id: int, source_ip: str) -> dict[str, Any]:
        name = payload["name"]
        decision = payload["decision"]

        adapter = self._resolve_adapter(name)
        await adapter.send_approval(decision)
        return {"status": "approved" if decision else "rejected"}

