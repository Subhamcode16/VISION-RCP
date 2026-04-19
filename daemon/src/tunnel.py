"""Vision-RCP Tunnel Manager — Auto-fallback tunnel: bore → ngrok."""

import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("rcp.tunnel")


@dataclass
class TunnelInfo:
    provider: str      # "bore" | "ngrok"
    public_url: str    # e.g. "https://abc.ngrok-free.app"
    local_port: int
    process: asyncio.subprocess.Process


class TunnelError(Exception):
    """Raised when a tunnel fails to start."""
    pass


class TunnelManager:
    """Manages external tunnel processes (bore, ngrok) for public access."""

    def __init__(self):
        self._active_tunnel: Optional[TunnelInfo] = None

    async def start(self, local_port: int, provider: str = "auto") -> TunnelInfo:
        """Start a tunnel with auto-fallback or specific provider."""
        if provider == "bore":
            return await self._start_bore(local_port)
        elif provider == "ngrok":
            return await self._start_ngrok(local_port)
        else:
            # Auto: try bore, then ngrok
            try:
                return await self._start_bore(local_port)
            except TunnelError as e:
                logger.warning("Bore failed: %s. Falling back to ngrok...", e)
                return await self._start_ngrok(local_port)

    async def stop(self):
        """Stop the active tunnel."""
        if self._active_tunnel:
            try:
                self._active_tunnel.process.terminate()
                await self._active_tunnel.process.wait()
            except Exception as e:
                logger.error("Error stopping tunnel: %s", e)
            finally:
                self._active_tunnel = None

    async def _start_bore(self, port: int) -> TunnelInfo:
        """Starts a bore tunnel (no account needed)."""
        logger.info("Starting bore tunnel for port %d...", port)
        try:
            # Command: bore local PORT --to bore.pub
            proc = await asyncio.create_subprocess_exec(
                "bore", "local", str(port), "--to", "bore.pub",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Bore prints the remote port/address in stdout
            # Example: "listening at bore.pub:12345"
            # We wait a bit for output
            try:
                # We read line by line until we find the URL
                while True:
                    line_bytes = await asyncio.wait_for(proc.stdout.readline(), timeout=5.0)
                    if not line_bytes:
                        break
                    line = line_bytes.decode().strip()
                    logger.debug("Bore: %s", line)
                    
                    if "listening at" in line.lower():
                        # Extract bore.pub:PORT
                        match = re.search(r"listening at ([\w\.-]+:\d+)", line)
                        if match:
                            url = f"http://{match.group(1)}"
                            # Note: bore typically uses http/tcp
                            info = TunnelInfo("bore", url, port, proc)
                            self._active_tunnel = info
                            return info
            except asyncio.TimeoutError:
                proc.terminate()
                raise TunnelError("Bore timed out waiting for public URL")
                
        except FileNotFoundError:
            raise TunnelError("Bore binary not found in PATH")
        except Exception as e:
            raise TunnelError(f"Bore failed: {e}")

    async def _start_ngrok(self, port: int) -> TunnelInfo:
        """Starts an ngrok tunnel (requires auth token)."""
        logger.info("Starting ngrok tunnel for port %d...", port)
        try:
            # Ngrok needs to be configured with 'ngrok config add-authtoken' elsewhere
            # or it might fail for new accounts.
            proc = await asyncio.create_subprocess_exec(
                "ngrok", "http", str(port), "--log", "stdout",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Ngrok logs URLs in its output
            # Look for "url=https://..."
            try:
                while True:
                    line_bytes = await asyncio.wait_for(proc.stdout.readline(), timeout=10.0)
                    if not line_bytes:
                        break
                    line = line_bytes.decode().strip()
                    logger.debug("Ngrok: %s", line)
                    
                    if "url=https://" in line:
                        match = re.search(r"url=(https://[\w\.-]+)", line)
                        if match:
                            url = match.group(1)
                            info = TunnelInfo("ngrok", url, port, proc)
                            self._active_tunnel = info
                            return info
            except asyncio.TimeoutError:
                proc.terminate()
                raise TunnelError("Ngrok timed out waiting for public URL")

        except FileNotFoundError:
            raise TunnelError("Ngrok binary not found in PATH")
        except Exception as e:
            raise TunnelError(f"Ngrok failed: {e}")
