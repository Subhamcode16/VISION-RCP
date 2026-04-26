import asyncio
import os
import sys
import re
import signal
import subprocess
import time
from pathlib import Path

# Configuration
RELAY_PORT = 8080
VERBOSE = True

def log(msg: str):
    print(f" [REMOTE-BOOT] {msg}", flush=True)

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
    """Starts cloudflared tunnel and extracts the URL via file-pipe."""
    log(f"Starting Cloudflare Tunnel for port {port}...")
    log("Using File-Pipe strategy for maximum reliability.")
    
    log_file = Path("tunnel_boot.log")
    if log_file.exists(): log_file.unlink()

    # Launch cloudflared and redirect ALL output to a file
    # We use 'start /b' to run in background in the same window context
    cmd = f"cloudflared tunnel --url http://localhost:{port} > {log_file} 2>&1"
    
    # We use Popen here because we want it to run detached from the pipe
    proc = subprocess.Popen(["cmd", "/c", cmd], creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0)
    
    tunnel_url = None
    start_time = time.time()
    
    try:
        log("Polling log file for public URL...")
        while time.time() - start_time < 30:
            print(".", end="", flush=True)
            await asyncio.sleep(1.0)
            
            if log_file.exists():
                content = log_file.read_text(errors='replace')
                if ".trycloudflare.com" in content:
                    match = re.search(r"(https://[a-zA-Z0-9.-]+\.trycloudflare\.com)", content)
                    if match:
                        tunnel_url = match.group(1)
                        print(f"\n [SUCCESS] Tunnel URL: {tunnel_url}")
                        return proc, tunnel_url
            
            # Check if process died
            if proc.poll() is not None:
                log("Cloudflare process terminted unexpectedly.")
                break
        
        log("TIMEOUT or FAILURE: Could not find tunnel URL in log.")
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
        # 1. Start Tunnel FIRST (provides the public URL needed by daemon)
        log("Establishing Cloudflare Tunnel (be patient)...")
        tunnel_proc, public_url = await run_tunnel(RELAY_PORT)
        if not public_url:
            log("FAILED: Could not establish tunnel.")
            return

        # 2. Start Relay
        log("Starting Relay server...")
        relay_proc = await run_relay()
        await asyncio.sleep(2) 

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
