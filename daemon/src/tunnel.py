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
        self._reconnect_task: Optional[asyncio.Task] = None
        self._is_stopping = False

    async def start(self, local_port: int, provider: str = "auto") -> TunnelInfo:
        """Start a tunnel with auto-fallback or specific provider."""
        if provider == "cloudflare":
            return await self._start_cloudflare(local_port)
        elif provider == "pinggy":
            return await self._start_pinggy(local_port)
        elif provider == "bore":
            return await self._start_bore(local_port)
        elif provider == "ngrok":
            return await self._start_ngrok(local_port)
        else:
            # Auto: try pinggy first (MVP default)
            try:
                return await self._start_cloudflare(local_port)
            except Exception as e:
                logger.warning("Cloudflare failed: %s. Falling back to pinggy...", e)
                try:
                    return await self._start_pinggy(local_port)
            except Exception as e:
                logger.warning("Pinggy failed: %s. Falling back to bore...", e)
                try:
                    return await self._start_bore(local_port)
                except TunnelError as e2:
                    logger.warning("Bore failed: %s. Falling back to ngrok...", e2)
                    return await self._start_ngrok(local_port)

    async def stop(self):
        """Stop the active tunnel and supervisor."""
        self._is_stopping = True
        if self._reconnect_task:
            self._reconnect_task.cancel()
            
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

    async def _start_pinggy(self, port: int) -> TunnelInfo:
        """Starts a Pinggy tunnel via SSH."""
        logger.info("Starting Pinggy tunnel for port %d...", port)
        try:
            # Command: ssh -p 443 -o StrictHostKeyChecking=no -R 80:localhost:PORT q@proxy.pinggy.io
            # We use 'q@' to get a simpler output and the link directly.
            # Host fallback: some networks block 'proxy.', so try raw 'pinggy.io'
            host = "proxy.pinggy.io"
            try:
                import socket
                socket.gethostbyname(host)
            except socket.gaierror:
                logger.warning("DNS resolution failed for %s, trying pinggy.io", host)
                host = "pinggy.io"
            
            # Reconnection logic started in background
            if not self._reconnect_task or self._reconnect_task.done():
                self._reconnect_task = asyncio.create_task(self._supervisor_loop(port, provider="pinggy"))

            proc = await asyncio.create_subprocess_exec(
                "ssh", "-p", "443", 
                "-o", "StrictHostKeyChecking=no",
                "-o", "ServerAliveInterval=30",
                "-o", "ServerAliveCountMax=3",
                "-o", "ExitOnForwardFailure=yes",
                "-R", f"80:localhost:{port}", f"q@{host}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Pinggy outputs the URL to either stdout or stderr depending on environment.
            # We'll monitor both for a few lines.
            try:
                # Give it up to 15 seconds to connect and print the URL
                for _ in range(30): # Read up to 30 lines total
                    # Try to read from stdout with a small timeout
                    try:
                        line_bytes = await asyncio.wait_for(proc.stdout.readline(), timeout=0.5)
                    except asyncio.TimeoutError:
                        line_bytes = None
                        
                    if not line_bytes:
                        # Try stderr
                        try:
                            line_bytes = await asyncio.wait_for(proc.stderr.readline(), timeout=0.5)
                        except asyncio.TimeoutError:
                            line_bytes = None
                            
                    if not line_bytes:
                        await asyncio.sleep(0.5)
                        continue
                        
                    line = line_bytes.decode(errors='replace').strip()
                    logger.debug("Pinggy Output: %s", line)
                    
                    # Pattern matches: https://....pinggy.link or .pinggy.io
                    if "https://" in line and "pinggy" in line:
                        match = re.search(r"(https://[\w\.-]+\.pinggy\.(?:link|io|online))", line)
                        if match:
                            url = match.group(1)
                            logger.info("Pinggy Tunnel Ready: %s", url)
                            info = TunnelInfo("pinggy", url, port, proc)
                            self._active_tunnel = info
                            return info
                            
                proc.terminate()
                raise TunnelError("Pinggy started but no public URL was found in output")
                
            except asyncio.TimeoutError:
                proc.terminate()
                raise TunnelError("Pinggy timed out connecting")
                
        except FileNotFoundError:
            raise TunnelError("SSH command not found. Please ensure OpenSSH is installed.")
        except Exception as e:
            raise TunnelError(f"Pinggy failed: {e}")

    async def _start_cloudflare(self, port: int) -> TunnelInfo:
        """Starts a Cloudflare Quick Tunnel (no account needed)."""
        logger.info("Starting Cloudflare tunnel for port %d...", port)
        try:
            # We use --url to specify the local service. 
            # cloudflared prints the URL to stderr.
            proc = await asyncio.create_subprocess_exec(
                "cloudflared", "tunnel", "--url", f"http://localhost:{port}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Cloudflare logs URLs in its output (usually stderr)
            # We look for "https://*.trycloudflare.com"
            try:
                # Give it up to 20 seconds as Cloudflare can be slow to handshake
                for _ in range(60): 
                    # Try stderr first (usual for logs)
                    try:
                        line_bytes = await asyncio.wait_for(proc.stderr.readline(), timeout=0.5)
                    except asyncio.TimeoutError:
                        line_bytes = None
                        
                    if not line_bytes:
                        # Try stdout
                        try:
                            line_bytes = await asyncio.wait_for(proc.stdout.readline(), timeout=0.1)
                        except asyncio.TimeoutError:
                            line_bytes = None
                    
                    if not line_bytes:
                        await asyncio.sleep(0.1)
                        continue
                        
                    line = line_bytes.decode(errors='replace').strip()
                    logger.debug("Cloudflare: %s", line)
                    
                    if ".trycloudflare.com" in line:
                        # Extract the hostname
                        match = re.search(r"(https://[\w\.-]+\.trycloudflare\.com)", line)
                        if match:
                            url = match.group(1)
                            logger.info("Cloudflare Tunnel Ready: %s", url)
                            info = TunnelInfo("cloudflare", url, port, proc)
                            self._active_tunnel = info
                            return info
                            
                proc.terminate()
                raise TunnelError("Cloudflare started but no public URL found in logs after 20s")
                
            except asyncio.TimeoutError:
                proc.terminate()
                raise TunnelError("Cloudflare timed out connecting")

        except FileNotFoundError:
            raise TunnelError("cloudflared binary not found in PATH")
        except Exception as e:
            raise TunnelError(f"Cloudflare failed: {e}")

    async def _supervisor_loop(self, port: int, provider: str):
        """Monitors the tunnel process and restarts it if it dies."""
        while not self._is_stopping:
            await asyncio.sleep(10)
            if self._active_tunnel and self._active_tunnel.process:
                if self._active_tunnel.process.returncode is not None:
                    logger.warning("Tunnel process died with code %s. Restarting...", self._active_tunnel.process.returncode)
                    try:
                        await self.start(port, provider=provider)
                    except Exception as e:
                        logger.error("Supervisor failed to restart tunnel: %s", e)
