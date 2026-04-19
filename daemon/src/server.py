"""Vision-RCP WebSocket Server — The daemon's network interface."""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from .config import Config
from .dependency_graph import DependencyGraphEngine
from .handlers import CommandHandler
from .models import LogEntry
from .process_manager import ProcessManager
from .protocol import Envelope, MessageType
from .security.audit import AuditLogger
from .security.auth import AuthManager
from .security.rate_limiter import RateLimiter
from .stream_router import StreamRouter

logger = logging.getLogger("rcp.server")


from .relay_client import RelayClient

class RCPServer:
    """FastAPI-based WebSocket server or Relay client for the Vision-RCP daemon."""

    def __init__(self, config: Config):
        self._config = config
        self._app = FastAPI(title="Vision-RCP Daemon", docs_url=None, redoc_url=None)
        self._connections: dict[int, WebSocket] = {}
        self._connection_counter = 0
        self._actual_port: int = 0
        self._relay_client: Optional[RelayClient] = None

        # Initialize subsystems
        logger.info("INIT_PULSE: Starting subsystem initialization")
        self._auth = AuthManager(
            config.data_dir,
            access_ttl=config.auth["access_token_ttl"],
            refresh_ttl=config.auth["refresh_token_ttl"],
        )
        logger.info("INIT_PULSE: AuthManager ready")
        
        self._stream_router = StreamRouter(
            buffer_size=config.processes["log_buffer_size"],
            max_buffer_bytes=config.processes["stream_buffer_max"],
        )
        logger.info("INIT_PULSE: StreamRouter ready")
        
        self._process_manager = ProcessManager(
            stream_router=self._stream_router,
            default_auto_restart=config.processes["auto_restart"],
            default_max_restarts=config.processes["max_restarts"],
            health_check_interval=config.processes["health_check_interval"],
        )
        logger.info("INIT_PULSE: ProcessManager ready")
        
        self._dep_graph = DependencyGraphEngine(self._process_manager)
        logger.info("INIT_PULSE: DependencyGraphEngine ready")
        
        self._audit = AuditLogger(
            config.data_dir,
            enabled=config.audit["enabled"],
            max_entries=config.audit["max_entries"],
            retention_days=config.audit["retention_days"],
        )
        logger.info("INIT_PULSE: AuditLogger ready")
        
        self._rate_limiter = RateLimiter(
            commands_per_minute=config.rate_limit["commands_per_minute"],
            burst=config.rate_limit["burst"],
            auth_attempts_per_minute=config.auth["max_auth_attempts"],
        )
        logger.info("INIT_PULSE: RateLimiter ready")

        self._handler: CommandHandler | None = None

        # Register process groups from config
        self._register_groups()

        # Set up routes
        self._setup_routes()

        # Set up process state change broadcasting
        self._process_manager.set_state_callback(self._broadcast_state_change)

    def _register_groups(self) -> None:
        """Parse and register process groups from TOML config."""
        for group_name, group_config in self._config.groups.items():
            processes_config = group_config.get("processes", {})
            if processes_config:
                process_defs = {}
                for proc_name, proc_config in processes_config.items():
                    process_defs[proc_name] = proc_config
                try:
                    self._dep_graph.register_group(group_name, process_defs)
                except ValueError as e:
                    logger.error("Failed to register group '%s': %s", group_name, e)

    def _setup_routes(self) -> None:
        app = self._app

        @app.websocket("/ws")
        async def websocket_endpoint(ws: WebSocket):
            await self._handle_connection(ws)

        @app.on_event("startup")
        async def startup():
            await self._audit.initialize()
            await self._process_manager.start_health_monitor()
            
            # Start relay client if enabled
            if self._config.relay["url"] and self._config.relay["token"]:
                from .device import DeviceIdentity
                device = DeviceIdentity(self._config.data_dir)
                self._relay_client = RelayClient(
                    handler=self._handler,
                    device=device,
                    relay_url=self._config.relay["url"],
                    relay_token=self._config.relay["token"],
                    secret_key=self.secret_key
                )
                
                # Link StreamRouter to relay for process output
                async def relay_stream_callback(entry: LogEntry):
                    msg = Envelope.stream_msg(ref="stream", payload=entry.to_dict())
                    await self._relay_client.send_stream(msg)
                
                self._stream_router.set_relay_callback(relay_stream_callback)
                
                await self._relay_client.start()
                logger.info("Relay client started")

            logger.info("Vision-RCP daemon started")

        @app.on_event("shutdown")
        async def shutdown():
            if self._relay_client:
                await self._relay_client.stop()
            await self._process_manager.shutdown()
            await self._audit.close()
            logger.info("Vision-RCP daemon stopped")

    def set_port(self, port: int) -> None:
        """Set the actual port after binding (for dynamic port)."""
        self._actual_port = port
        
        def provide_session():
            res = {}
            if self._relay_client:
                res.update({
                    "session_id": self._relay_client.session_id,
                    "device_name": self._config.network.get("device_name", "unknown")
                })
            
            # Inject active agent status if handler is available
            if self._handler and self._handler._active_adapters:
                agent_name = next(iter(self._handler._active_adapters.keys()))
                adapter = self._handler._active_adapters[agent_name]
                res["agent_name"] = agent_name
                res["agent_status"] = "running" if adapter.is_running else "stopped"
            
            return res

        self._handler = CommandHandler(
            config=self._config,
            auth=self._auth,
            process_manager=self._process_manager,
            dep_graph=self._dep_graph,
            stream_router=self._stream_router,
            audit=self._audit,
            rate_limiter=self._rate_limiter,
            daemon_port=port,
            session_provider=provide_session,
        )
        
        if self._relay_client:
            self._relay_client.set_handler(self._handler)

    @property
    def app(self) -> FastAPI:
        return self._app

    @property
    def secret_key(self) -> str:
        return self._auth.display_secret

    async def _handle_connection(self, ws: WebSocket) -> None:
        """Handle a single WebSocket connection lifecycle."""
        await ws.accept()

        self._connection_counter += 1
        conn_id = self._connection_counter
        self._connections[conn_id] = ws

        source_ip = ws.client.host if ws.client else "unknown"
        logger.info("Connection %d opened from %s", conn_id, source_ip)
        await self._audit.log("connection.open", source_ip=source_ip)

        # Subscribe this connection to all process streams
        async def stream_callback(entry: LogEntry) -> None:
            if ws.client_state == WebSocketState.CONNECTED:
                msg = Envelope.stream_msg(
                    ref="stream",
                    payload=entry.to_dict(),
                )
                try:
                    await ws.send_text(msg.to_json())
                except Exception:
                    pass

        self._stream_router.subscribe_all(conn_id, stream_callback)

        # Heartbeat task
        heartbeat_task = asyncio.create_task(self._heartbeat_loop(ws, conn_id))

        try:
            while True:
                raw = await ws.receive_text()

                try:
                    envelope = Envelope.from_json(raw)
                except Exception as e:
                    err = Envelope.err("unknown", "PARSE_ERROR",
                                       f"Invalid message format: {e}")
                    await ws.send_text(err.to_json())
                    continue

                if not self._handler:
                    err = Envelope.err(envelope.id, "NOT_READY",
                                       "Server is still initializing")
                    await ws.send_text(err.to_json())
                    continue

                response = await self._handler.handle(envelope, conn_id, source_ip)
                await ws.send_text(response.to_json())

        except WebSocketDisconnect:
            logger.info("Connection %d closed (client disconnect)", conn_id)
        except Exception as e:
            logger.error("Connection %d error: %s", conn_id, e)
        finally:
            heartbeat_task.cancel()
            self._stream_router.unsubscribe(conn_id)
            self._rate_limiter.remove_connection(str(conn_id))
            self._connections.pop(conn_id, None)
            await self._audit.log("connection.close", source_ip=source_ip)

    async def _heartbeat_loop(self, ws: WebSocket, conn_id: int) -> None:
        """Send periodic heartbeats to detect stale connections."""
        try:
            while True:
                await asyncio.sleep(10)
                if ws.client_state == WebSocketState.CONNECTED:
                    hb = Envelope.heartbeat()
                    await ws.send_text(hb.to_json())
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    async def _broadcast_state_change(self, proc: Any) -> None:
        """Broadcast process state changes to all connected clients."""
        msg = Envelope.stream_msg(
            ref="state_change",
            payload={
                "event": "state_change",
                "process": proc.to_dict() if hasattr(proc, "to_dict") else {},
            },
        )
        json_msg = msg.to_json()

        # Broadcast to local clients
        dead_conns = []
        for conn_id, ws in self._connections.items():
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_text(json_msg)
            except Exception:
                dead_conns.append(conn_id)

        for conn_id in dead_conns:
            self._connections.pop(conn_id, None)

        # Push to relay if connected
        if self._relay_client:
            await self._relay_client.send_stream(msg)
