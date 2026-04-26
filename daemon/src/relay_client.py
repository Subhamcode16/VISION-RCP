"""Vision-RCP Relay Client — Outbound daemon connection to relay server.

This replaces the old relay_connector by processing commands directly from 
 the relay WebSocket, eliminating the local loopback.
"""

import asyncio
import json
import logging
from typing import Optional

import websockets
from websockets.exceptions import ConnectionClosed

from .device import DeviceIdentity
from .handlers import CommandHandler
from .protocol import Envelope


logger = logging.getLogger("rcp.relay_client")


class RelayClient:
    """Manages the persistent outbound connection from daemon to relay."""

    def __init__(self, handler: Optional[CommandHandler], 
                 device: DeviceIdentity, 
                 relay_url: str,
                 relay_token: str,
                 secret_key: Optional[str] = None):
        self._handler = handler
        self._device = device
        self._relay_url = relay_url
        self._relay_token = relay_token
        self._secret_key = secret_key
        self._running = False
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._session_id: Optional[str] = None

    async def start(self):
        """Start the relay client connection loop."""
        self._running = True
        asyncio.create_task(self._run_loop())

    async def stop(self):
        """Stop the relay client."""
        self._running = False
        if self._ws:
            await self._ws.close()

    async def _run_loop(self):
        """Main connection loop with exponential backoff."""
        delay = 1.0
        while self._running:
            try:
                await self._connect_and_serve()
                delay = 1.0  # Reset delay on success
            except Exception as e:
                logger.error("Relay connection error: %s", e)
                
            if not self._running:
                break
                
            logger.info("Reconnecting to relay in %.1fs...", delay)
            await asyncio.sleep(delay)
            delay = min(delay * 2, 60.0)

    async def _connect_and_serve(self):
        """Connect to relay, perform handshake, and enter command loop."""
        # Ensure URL construction is robust
        base_url = self._relay_url.rstrip("/")
        if not base_url.endswith("/ws/daemon"):
            url_path = "/ws/daemon"
        else:
            url_path = ""
            
        url = (f"{base_url}{url_path}?token={self._relay_token}"
               f"&fingerprint={self._device.fingerprint}"
               f"&name={self._device.device_name}")
               
        # ping_interval=10, ping_timeout=20 to keep tunnels (bore/ngrok) alive
        async with websockets.connect(url, ping_interval=10, ping_timeout=20) as ws:
            self._ws = ws
            logger.info("Connected to relay server")
            
            # 1. Wait for handshake response (session assignment)
            try:
                # 5s timeout on handshake response to prevent hanging indefinitely
                msg_raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
                handshake = json.loads(msg_raw)
                if handshake.get("type") == "handshake":
                    self._session_id = handshake["session_id"]
                    client_token = handshake.get("token", "N/A")
                    logger.info("Session assigned: %s (Token: %s)", self._session_id, client_token)
                    
                    # Generate and log the full remote access link for scanning/copying
                    import os
                    dashboard = os.environ.get("VITE_DASHBOARD_URL")
                    relay_public = os.environ.get("RELAY_PUBLIC_URL")
                    
                    if dashboard and self._secret_key:
                        # Construct the relay parameter for the frontend
                        # If a public tunnel is active, use it. Otherwise fallback to the direct relay URL.
                        r_param = ""
                        if relay_public:
                            # Convert http -> wss for secure frontend connectivity
                            relay_ws = relay_public.replace("http://", "wss://").replace("https://", "wss://")
                            r_param = f"&r={relay_ws.rstrip('/')}/ws/client"
                        
                        full_link = (f"{dashboard.rstrip('/')}/"
                                     f"?s={self._session_id}"
                                     f"&t={client_token}"
                                     f"&k={self._secret_key}"
                                     f"{r_param}")
                        
                        # Use print for visibility over standard logging in some terminal environments
                        print("\n" + "="*60)
                        print(f" [REMOTE DASHBOARD READY]")
                        print(f" URL: {full_link}")
                        
                        try:
                            import qrcode
                            qr = qrcode.QRCode(version=1, box_size=1, border=2)
                            # Truncate link for QR if it's too long, but keep params
                            qr.add_data(full_link)
                            qr.make(fit=True)
                            print("\n [REMOTE SCAN] Scan to take control from mobile:")
                            qr.print_ascii(invert=True)
                        except Exception as qr_err:
                            logger.warning("Could not generate QR code: %s", qr_err)
                            
                        print("="*60 + "\n")
                        logger.info("Remote dashboard link generated")
            except Exception as e:
                logger.error("Handshake failed: %s", e)
                return

            # 2. Command loop
            async for message in ws:
                try:
                    envelope = Envelope.from_json(message)
                    # Process command
                    if not self._handler:
                        logger.warning("Dropped relay command: Handler not ready")
                        continue
                        
                    # Use a session-prefixed connection ID so the rate limiter
                    # can identify aggregated relay traffic.
                    conn_id_str = f"relay:{self._session_id or 'init'}"
                    
                    try:
                        response = await self._handler.handle(envelope, connection_id=conn_id_str, source_ip="relay")
                        # Send response back to relay (which forwards to client)
                        await ws.send(response.to_json())
                    except Exception as handler_err:
                        # CRITICAL: Always send an error envelope back so the UI doesn't hang for 30s
                        logger.error("Handler exception (Relay): %s", handler_err)
                        err_env = Envelope.err(
                            ref=envelope.id,
                            code="HANDLER_ERROR",
                            message=str(handler_err)
                        )
                        await ws.send(err_env.to_json())
                except Exception as e:
                    logger.error("Error processing relay command string: %s", e)

    async def send_stream(self, envelope: Envelope):
        """Push a stream message to the relay."""
        if self._ws and not getattr(self._ws, 'closed', False):
            try:
                await self._ws.send(envelope.to_json())
            except Exception:
                pass

    def set_handler(self, handler: CommandHandler):
        """Update the command handler (used when dynamic port is resolved)."""
        self._handler = handler

    @property
    def session_id(self) -> Optional[str]:
        return self._session_id

    @property
    def relay_token(self) -> str:
        return self._relay_token
