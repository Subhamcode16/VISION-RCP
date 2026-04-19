"""Vision-RCP Daemon — Entry point.

Usage:
    python -m src.main [--config path/to/config.toml]
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import socket
import sys
from pathlib import Path

import uvicorn

from .config import Config
from .server import RCPServer


def setup_logging(log_level: str, data_dir: Path):
    """Configure rich logging."""
    import logging.handlers
    
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_fmt = logging.Formatter("%(asctime)s │ %(levelname)-7s │ %(name)-20s │ %(message)s", datefmt="%H:%M:%S")
    console_handler.setFormatter(console_fmt)
    
    # File handler
    log_file = data_dir / "daemon.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=5*1024*1024, backupCount=2, encoding="utf-8"
    )
    file_fmt = logging.Formatter("[%(asctime)s] %(levelname)s [%(name)s] - %(message)s")
    file_handler.setFormatter(file_fmt)

    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[console_handler, file_handler],
        force=True
    )


BANNER = r"""
 V I S I O N - R C P
 Local Agent Control Plane
"""


def find_free_port() -> int:
    """Find a random available port by binding to port 0."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


import time

class StartupPulse:
    """Helper to track startup timing and log pulses."""
    def __init__(self):
        self.start_time = time.perf_counter()
        self.last_pulse = self.start_time

    def pulse(self, name: str):
        now = time.perf_counter()
        total_elapsed = now - self.start_time
        delta = now - self.last_pulse
        self.last_pulse = now
        print(f"  [PULSE] {name:<30} │ +{delta:6.3f}s │ Total: {total_elapsed:6.3f}s")
        logging.info("STARTUP_PULSE: %s (delta: %.3fs, total: %.3fs)", name, delta, total_elapsed)

def main() -> None:
    pulse = StartupPulse()
    
    parser = argparse.ArgumentParser(description="Vision-RCP Daemon")
    parser.add_argument(
        "--config", "-c",
        default="config.toml",
        help="Path to TOML configuration file (default: config.toml)",
    )
    args = parser.parse_args()

    # Load configuration
    config_path = Path(args.config)
    if not config_path.exists():
        daemon_dir = Path(__file__).parent.parent
        config_path = daemon_dir / "config.toml"

    config = Config(config_path if config_path.exists() else None)
    pulse.pulse("Config loaded")

    # Setup logging
    setup_logging(config.daemon["log_level"], config.data_dir)
    pulse.pulse("Logging initialized")

    # PRE-START: Generate/Load Secret Key immediately for the banner
    # We do this before the full RCPServer initialization to avoid the 30min hang
    from .security.auth import AuthManager
    auth_temp = AuthManager(config.data_dir)
    secret_key = auth_temp.display_secret
    pulse.pulse("AuthManager (pre-init) ready")

    # Determine port
    port = config.daemon["port"] or find_free_port()
    host = config.daemon["host"]
    log_level = config.daemon["log_level"]

    # Display startup info IMMEDIATELY
    print(BANNER)
    print(f"  +----------------------------------------------------------+")
    print(f"  |  Host:     {host:<46}|")
    print(f"  |  Port:     {port:<46}|")
    print(f"  |  Data:     {str(config.data_dir):<46}|")
    print(f"  +----------------------------------------------------------+")
    print(f"  |  WebSocket: ws://{host}:{port}/ws                          |")
    print(f"  +----------------------------------------------------------+")
    print(f"  |  ONE-CLICK DASHBOARD (LOCAL):                            |")
    print(f"  |  http://localhost:5173/?k={secret_key:<31}|")
    print(f"  +----------------------------------------------------------+")
    
    # Remote / Mobile Dashboard Link
    remote_dashboard = os.environ.get("VITE_DASHBOARD_URL")
    if remote_dashboard:
        remote_dashboard = remote_dashboard.rstrip("/")
        # We don't have the session_id yet (it comes from the relay handshake),
        # but we can print the base URL + Key for quick mobile login once paired.
        print(f"  |  REMOTE DASHBOARD (MOBILE):                              |")
        print(f"  |  {remote_dashboard[:54]:<54}|")
        if len(remote_dashboard) > 54:
            print(f"  |  {remote_dashboard[54:108]:<54}|")
        print(f"  +----------------------------------------------------------+")
        
        # Print QR Code if requested and library is available
        try:
            import qrcode
            qr = qrcode.QRCode(version=1, box_size=1, border=2)
            # Use a slightly more generic login link that just needs the key
            qr_link = f"{remote_dashboard}/?k={secret_key}"
            qr.add_data(qr_link)
            qr.make(fit=True)
            print("  [REMOTE SCAN] Scan to open on mobile:")
            qr.print_ascii(invert=True)
            print(f"  +----------------------------------------------------------+")
        except Exception:
            pass

    print(f"  |  Secret Key (manual copy):                               |")
    print(f"  |  {secret_key[:54]:<54}|")
    if len(secret_key) > 54:
        print(f"  |  {secret_key[54:]:<54}|")
    print(f"  +----------------------------------------------------------+")
    print()

    pulse.pulse("Banner displayed")

    # Now do the heavy lifting
    print("  Initializing core systems... (checking hardware and processes)")
    server = RCPServer(config)
    server.set_port(port)
    pulse.pulse("RCPServer initialized")

    # Write port to a discoverable file
    port_file = config.data_dir / "daemon.port"
    port_file.write_text(str(port))

    # Run server
    uvicorn.run(
        server.app,
        host=host,
        port=port,
        log_level=log_level,
        ws_max_size=16 * 1024 * 1024,
        lifespan="on",
    )


if __name__ == "__main__":
    main()
