"""Vision-RCP CLI — The primary interface for controlling the daemon."""

import asyncio
import os
import sys
import webbrowser
import socket
import subprocess
import signal
import time
from pathlib import Path
from typing import List, Optional

import click
import uvicorn

from .config import Config
from .device import DeviceIdentity
from .qr import QRGenerator
from .server import RCPServer
from .tunnel import TunnelManager


def get_default_data_dir():
    return Path(os.path.expanduser("~/.vision-rcp"))


def get_project_root():
    """Calculate the absolute project root relative to this CLI file."""
    return Path(__file__).resolve().parent.parent.parent


def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def kill_port_owner(port: int):
    """Find and kill the process listening on a specific port (Windows)."""
    try:
        # Find PID using netstat
        output = subprocess.check_output(f'netstat -aon | findstr LISTENING | findstr :{port}', shell=True).decode()
        for line in output.strip().split('\n'):
            parts = line.split()
            if len(parts) > 4:
                pid = parts[-1]
                click.secho(f"    [!] Port {port} is busy (PID {pid}). Killing...", fg="yellow")
                subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True)
                time.sleep(0.5)
    except subprocess.CalledProcessError:
        pass


@click.group()
@click.pass_context
def cli(ctx):
    """Vision-RCP — Remote Control Plane for your local machine."""
    data_dir = get_default_data_dir()
    config_path = data_dir / "config.toml"
    ctx.obj = {
        'data_dir': data_dir,
        'config': Config(config_path=config_path if config_path.exists() else None),
        'device': DeviceIdentity(data_dir=data_dir),
        'project_root': get_project_root()
    }


@cli.command()
@click.pass_context
def init(ctx):
    """Initialize Vision-RCP on this device."""
    data_dir = ctx.obj['data_dir']
    device = ctx.obj['device']
    
    click.echo(f"Initializing Vision-RCP in {data_dir}...")
    
    # 1. Ensure directory exists
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # 2. Init device identity (gen keys)
    fingerprint = device.init()
    
    click.secho("[OK] Device identity generated.", fg="green")
    click.echo(f"Fingerprint: {fingerprint}")
    
    # 3. Write default config if missing
    click.echo("Setup complete. Use 'vision-rcp start' to begin.")


@cli.command()
@click.option('--name', default=None, help='Session name')
@click.option('--relay-url', default=None, help='Relay URL override')
@click.option('--relay-token', default=None, help='Relay Token override')
@click.option('--local', is_flag=True, help='Local-only mode (localhost)')
@click.option('--headless', is_flag=True, help='No QR or auto-open browser')
@click.pass_context
def start(ctx, name, relay_url, relay_token, local, headless):
    """Start a remote control session."""
    config = ctx.obj['config']
    device = ctx.obj['device']
    
    # Overrides
    if name: config.daemon['session_name'] = name
    if relay_url: config.relay['url'] = relay_url
    if relay_token: config.relay['token'] = relay_token
    
    click.secho("\n" + "=" * 45, fg="cyan")
    click.secho("    Vision RCP -- Remote Control Ready ", fg="cyan", bold=True)
    click.secho("=" * 45 + "\n", fg="cyan")
    
    click.echo(f"[*] Session:  {config.daemon.get('session_name') or device.device_name}")
    click.echo(f"[*] Machine:  {device.device_name}")
    
    # Check for keys
    if not device.fingerprint:
        click.secho("[!] Error: Device identity not found. Run 'vision-rcp init' first.", fg="red")
        return

    # Start the daemon core
    server = RCPServer(config)
    
    async def run_session():
        # 1. Setup Uvicorn
        cfg_uvicorn = uvicorn.Config(
            server.app, 
            host=config.daemon['host'], 
            port=config.daemon['port'], 
            log_level="error"
        )
        uvicorn_server = uvicorn.Server(cfg_uvicorn)
        
        # Start uvicorn in background
        serve_task = asyncio.create_task(uvicorn_server.serve())
        
        # Wait a bit for server to start
        while not uvicorn_server.started:
            await asyncio.sleep(0.1)
            
        # Get the actual port if it was 0
        actual_port = uvicorn_server.config.port
        if actual_port == 0 and uvicorn_server.servers:
            for server_proc in uvicorn_server.servers:
                for socket in server_proc.sockets:
                    actual_port = socket.getsockname()[1]
                    break
        
        # Ensure server port is set in handler
        server.set_port(actual_port)
        
        # 2. Display Connection Info
        click.secho("[+] Daemon:   Online", fg="green")
        click.echo(f"    Local:    ws://{config.daemon['host']}:{actual_port}/ws")
        click.echo(f"    Secret:   {server.secret_key}")
        
        # 3. Handle Relay/Remote mode
        if not local:
             # Default to Vercel UI for remote access
             ui_base = config.daemon.get('ui_url', 'https://vision-rcp-ui.vercel.app')
             ws_local = f"ws://localhost:{actual_port}/ws"
             remote_url = f"{ui_base}?r={ws_local}&k={server.secret_key}&a=antigravity"
             
             click.secho("[+] Remote Ready", fg="blue")
             if not headless:
                 click.echo("\n[*] Scan to control from Browser/Phone:\n")
                 qr_text = QRGenerator.to_terminal(remote_url)
                 click.echo(qr_text)
                 click.echo(f"\n[!] Join Link: {remote_url}\n")
        
        # 4. Wait for uvicorn to finish
        await serve_task

    try:
        asyncio.run(run_session())
    except KeyboardInterrupt:
        click.echo("\nStopping session...")
    except Exception as e:
        click.secho(f"Error: {e}", fg="red")


# ═══════════════════════════════════════════════════════════════
# /rcp — The One-Shot Remote Agent Bridge
# ═══════════════════════════════════════════════════════════════

@cli.command()
@click.option('--workspace', '-w', default='.', help='Project workspace path for the agent')
@click.option('--agent', '-a', default='antigravity_pty', help='Agent adapter name')
@click.option('--agent-cmd', default=None, help='Override agent CLI command')
@click.option('--relay-url', default=None, help='Relay URL override')
@click.option('--relay-token', default=None, help='Relay Token override')
@click.option('--local', is_flag=True, help='Local-only mode (no relay)')
@click.option('--headless', is_flag=True, help='No QR code or auto-open browser')
@click.option('--no-browser', is_flag=True, default=True, help='Skip auto-opening browser (Default: True)')
@click.pass_context
def rcp(ctx, workspace, agent, agent_cmd, relay_url, relay_token, local, headless, no_browser):
    """Start a remote-controlled Antigravity agent session."""
    run_rcp_logic(ctx, workspace, agent, agent_cmd, relay_url, relay_token, local, headless, no_browser)


@cli.command(name="connect")
@click.option('--workspace', '-w', default='.', help='Project workspace path for the agent')
@click.option('--agent', '-a', default='antigravity_pty', help='Agent adapter name')
@click.option('--agent-cmd', default=None, help='Override agent CLI command')
@click.option('--local', is_flag=True, help='Local-only mode (no remote tunnel)')
@click.pass_context
def connect(ctx, workspace, agent, agent_cmd, local):
    """Start the full Vision-RCP stack and connect a remote agent."""
    root = ctx.obj['project_root']
    
    click.secho("\n[*] Initializing Vision-RCP Stack...", fg="cyan", bold=True)
    
    # 1. Check Port Conflicts
    daemon_port = ctx.obj['config'].daemon.get('port', 9077)
    relay_port = 8080
    ui_port = 5173
    
    for p in [daemon_port, relay_port, ui_port]:
        if is_port_in_use(p):
            click.echo(f"    [!] Port {p} is busy. Clearing...")
            kill_port_owner(p)

    # Track sub-processes for cleanup
    subprocesses = []

    try:
        # 2. Start Relay Server
        click.echo("    [+] Starting Relay Server...")
        venv_python = root / "daemon" / ".venv" / "Scripts" / "python.exe"
        if not venv_python.exists():
            venv_python = "python"
        
        relay_proc = subprocess.Popen(
            [str(venv_python), "-m", "relay.server"],
            cwd=str(root),
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        subprocesses.append(relay_proc)
        time.sleep(1)

        # 3. Start UI Dev Server
        click.echo("    [+] Starting UI Dev Server...")
        ui_proc = subprocess.Popen(
            ["cmd", "/c", "npm", "run", "dev"],
            cwd=str(root / "ui"),
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        subprocesses.append(ui_proc)
        time.sleep(2)

        # 4. Run main RCP logic (Managed)
        run_rcp_logic(ctx, workspace, agent, agent_cmd, None, None, local, False, False)

    except KeyboardInterrupt:
        click.echo("\n[*] Shutting down stack...")
    finally:
        # Cleanup ALL managed processes
        for proc in subprocesses:
            try:
                # On Windows, taskkill is more reliable for console windows
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(proc.pid)], 
                             capture_output=True, check=False)
            except Exception:
                proc.kill()
        click.secho("[DONE] Stack stops.", fg="yellow")


def run_rcp_logic(ctx, workspace, agent, agent_cmd, relay_url, relay_token, local, headless, no_browser):
    config = ctx.obj['config']
    device = ctx.obj['device']
    workspace_path = os.path.abspath(workspace)
    
    click.echo("")
    click.secho("+-----------------------------------------------+", fg="cyan")
    click.secho("|                                               |", fg="cyan")
    click.secho("|      Vision RCP - Remote Agent Bridge         |", fg="cyan", bold=True)
    click.secho("|                                               |", fg="cyan")
    click.secho("+-----------------------------------------------+", fg="cyan")
    click.echo("")
    click.echo(f"  Machine:    {device.device_name}")
    click.echo(f"  Workspace:  {workspace_path}")
    click.echo(f"  Agent:      {agent}")
    click.echo("")
    
    if not device.fingerprint:
        device.init()
    
    server = RCPServer(config)
    
    async def run_rcp_session():
        is_local = local 
        
        # Session reaper
        async def session_reaper(limit_secs: int):
            await asyncio.sleep(limit_secs)
            await uvicorn_server.shutdown()
            os._exit(0)

        asyncio.create_task(session_reaper(24 * 60 * 60))

        click.echo("[1/5] Starting daemon...")
        cfg_uvicorn = uvicorn.Config(server.app, host=config.daemon['host'], port=config.daemon['port'], log_level="error")
        uvicorn_server = uvicorn.Server(cfg_uvicorn)
        serve_task = asyncio.create_task(uvicorn_server.serve())
        
        while not uvicorn_server.started: await asyncio.sleep(0.1)
        
        actual_port = uvicorn_server.config.port
        if actual_port == 0 and uvicorn_server.servers:
            for sp in uvicorn_server.servers:
                for sock in sp.sockets:
                    actual_port = sock.getsockname()[1]
                    break
        
        server.set_port(actual_port)
        click.secho(f"      [OK] Daemon online (port {actual_port})", fg="green")
        
        dashboard_url = None
        if not is_local:
            click.echo("[2/5] Establishing remote access...")
            tunnel_manager = TunnelManager()
            try:
                tunnel_info = await tunnel_manager.start(actual_port, provider="pinggy")
                public_url = tunnel_info.public_url
                
                # Force WSS for public link
                ws_tunnel = public_url.replace("https://", "wss://").replace("http://", "ws://")
                if not ws_tunnel.endswith("/ws"): ws_tunnel = f"{ws_tunnel}/ws"

                ui_base = config.daemon.get('ui_url', 'https://vision-rcp-ui.vercel.app')
                dashboard_url = f"{ui_base}?r={ws_tunnel}&k={server.secret_key}&a={agent}"
                
                click.secho(f"      [OK] Pinggy Tunnel: {public_url}", fg="green")
                click.secho(f"      Remote Dashboard: {dashboard_url}", fg="cyan", bold=True)
            except Exception as e:
                click.secho(f"      [!] Tunnel failed: {e}", fg="yellow")
                is_local = True

        # Agent spawn
        click.echo(f"[3/5] Spawning agent ({agent})...")
        agent_config = {"working_dir": workspace_path}
        
        try:
            from .models import LogEntry
            from .adapters import AdapterRegistry
            
            async def emit_callback(entry: LogEntry):
                color = "cyan" if entry.stream == "stderr" else None
                try: click.secho(entry.data, fg=color)
                except: pass
                await server._stream_router.emit(entry)
            
            adapter = AdapterRegistry.get(agent, emit_callback)
            await adapter.start(agent_config)
            
            if server._handler:
                server._handler._active_adapters[agent] = adapter
                asyncio.create_task(adapter.stream_output())
            
            click.secho(f"      [OK] Agent spawned (PID: {getattr(adapter, 'pid', 'N/A')})", fg="green")
        except Exception as e:
            click.secho(f"      [!] Agent spawn failed: {e}", fg="red")

        # Access Info
        click.echo("[4/5] Generating access...")
        local_ui_base = config.daemon.get('local_ui_url', 'http://localhost:5173')
        ws_local = f"ws://localhost:{actual_port}/ws"
        local_dashboard_url = f"{local_ui_base}?r={ws_local}&k={server.secret_key}&a={agent}"
        
        click.echo("")
        click.secho(f"  [+] Local Dashboard:  {local_dashboard_url}", fg="green", bold=True)
        
        if dashboard_url:
            if not headless:
                click.echo("")
                click.secho("  +-------------------------------------+", fg="magenta")
                click.secho("  |   Scan QR for phone control:        |", fg="magenta")
                click.secho("  +-------------------------------------+", fg="magenta")
                click.echo("")
                try:
                    click.echo(QRGenerator.to_terminal(dashboard_url))
                except: pass
                
                click.echo("")
                click.secho(f"  [+] Remote Dashboard: {dashboard_url}", fg="cyan", bold=True)
                click.echo(f"  [+] Secret Key:       {server.secret_key}")
                click.echo("")
            else:
                click.secho(f"  [+] Remote Dashboard: {dashboard_url}", fg="cyan", bold=True)
        else:
            click.echo(f"  [+] Secret Key:       {server.secret_key}")
            click.secho("      (Tunnel offline - only local access available)", fg="yellow")

        # Browser
        if not headless and not no_browser:
            click.echo("[5/5] Opening dashboard...")
            try: webbrowser.open(local_dashboard_url)
            except: pass
        
        click.echo("")
        click.secho("-" * 48, fg="green")
        click.secho("  [OK] Vision RCP is LIVE", fg="green", bold=True)
        click.secho("-" * 48, fg="green")
        
        await serve_task

    try:
        asyncio.run(run_rcp_session())
    except KeyboardInterrupt:
        click.echo("\nStopping...")


@cli.command()
def status():
    """Show active session status."""
    click.echo("Feature coming soon.")


@cli.command()
def stop():
    """Stop the active session."""
    click.echo("Feature coming soon.")


if __name__ == "__main__":
    cli()
