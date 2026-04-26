import asyncio
import os
import sys
import re
import signal
import subprocess
from pathlib import Path

# Configuration
RELAY_PORT = 8080
VERBOSE = True

def log(msg: str):
    print(f" [REMOTE-BOOT] {msg}")

async def run_relay():
    """Starts the relay server process."""
    log(f"Starting Relay on port {RELAY_PORT}...")
    # Clean up any existing relay on 8080 (Windows specific)
    try:
        subprocess.run(["cmd", "/c", f"for /f \"tokens=5\" %a in ('netstat -aon ^| findstr :{RELAY_PORT}') do taskkill /f /pid %a"], 
                       stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    except:
        pass

    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "uvicorn", "server:app", "--port", str(RELAY_PORT), "--host", "0.0.0.0",
        cwd=str(Path("relay")),
        stdout=None, # Direct to terminal to avoid buffer hang
        stderr=None
    )
    return proc

async def run_tunnel(port: int):
    """Starts cloudflared tunnel and extracts the URL."""
    log(f"Starting Cloudflare Quick Tunnel for port {port}...")
    proc = await asyncio.create_subprocess_exec(
        "cloudflared", "tunnel", "--url", f"http://localhost:{port}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    tunnel_url = None
    # We read stderr where cloudflared logs the URL
    try:
        # Give it up to 30 seconds
        for _ in range(120):
            try:
                line_bytes = await asyncio.wait_for(proc.stderr.readline(), timeout=0.25)
                if not line_bytes: break
                line = line_bytes.decode(errors='replace').strip()
                if VERBOSE: print(f"  [cloudflared] {line}")
                
                if ".trycloudflare.com" in line:
                    match = re.search(r"(https://[\w\.-]+\.trycloudflare\.com)", line)
                    if match:
                        tunnel_url = match.group(1)
                        log(f"Tunnel established: {tunnel_url}")
                        return proc, tunnel_url
            except asyncio.TimeoutError:
                continue
    except Exception as e:
        log(f"Tunnel error: {e}")
    
    return proc, None

async def run_daemon(relay_public_url: str):
    """Starts the main daemon with remote variables."""
    log("Starting Daemon with remote relay link...")
    env = os.environ.copy()
    env["RELAY_PUBLIC_URL"] = relay_public_url
    env["RELAY_URL"] = f"ws://127.0.0.1:{RELAY_PORT}"
    env["VITE_DASHBOARD_URL"] = "https://vision-rcp-ui.vercel.app/"
    
    # Run as a module from the daemon directory to fix relative imports
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "src.main",
        cwd=str(Path("daemon")),
        env=env,
        stdout=sys.stdout,
        stderr=sys.stderr
    )
    return proc

async def main():
    log("=== Vision-RCP Remote Bridge Side Quest ===")
    
    relay_proc = None
    tunnel_proc = None
    daemon_proc = None
    
    try:
        # 1. Start Relay
        relay_proc = await run_relay()
        await asyncio.sleep(2) # Give relay a moment to bind
        
        # 2. Start Tunnel
        if not os.path.exists(os.path.expanduser("~") + "/bin/cloudflared.exe") and \
           not subprocess.run(["where", "cloudflared"], capture_output=True, shell=True).returncode == 0:
            log("CRITICAL: 'cloudflared' not found. Please install it to enable mobile access.")
            return

        log("Establishing Cloudflare Tunnel (be patient)...")
        tunnel_proc, public_url = await run_tunnel(RELAY_PORT)
        if not public_url:
            log("FAILED: Could not establish tunnel.")
            return

        # 3. Start Daemon
        log("Booting Vision-RCP Daemon...")
        daemon_proc = await run_daemon(public_url)
        
        # 4. Wait for daemon to finish or for interrupt
        await daemon_proc.wait()
        
    except KeyboardInterrupt:
        log("Shutting down remote bridge...")
    finally:
        # Safely shut down all processes
        for p in [daemon_proc, tunnel_proc, relay_proc]:
            if p and p.returncode is None:
                try:
                    p.terminate()
                    await p.wait()
                except:
                    pass
        log("All processes stopped.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
