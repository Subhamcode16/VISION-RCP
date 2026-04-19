"""Vision-RCP CLI — The primary interface for controlling the daemon."""

import asyncio
import os
import sys
import webbrowser
from pathlib import Path

import click
import uvicorn

from .config import Config
from .device import DeviceIdentity
from .qr import QRGenerator
from .server import RCPServer
from .tunnel import TunnelManager


def get_default_data_dir():
    return Path(os.path.expanduser("~/.vision-rcp"))


@click.group()
@click.pass_context
def cli(ctx):
    """Vision-RCP — Remote Control Plane for your local machine."""
    data_dir = get_default_data_dir()
    config_path = data_dir / "config.toml"
    ctx.obj = {
        'data_dir': data_dir,
        'config': Config(config_path=config_path if config_path.exists() else None),
        'device': DeviceIdentity(data_dir=data_dir)
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
        actual_port = c_port = uvicorn_server.config.port
        if c_port == 0 and uvicorn_server.servers:
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
        if not local and config.relay['url']:
            wait_count = 0
            while wait_count < 10:
                if server._relay_client and server._relay_client.session_id:
                    break
                await asyncio.sleep(1)
                wait_count += 1
            
            if server._relay_client and server._relay_client.session_id:
                sid = server._relay_client.session_id
                rtok = server._relay_client.relay_token
                
                ui_base = config.daemon.get('ui_url', 'https://rcp.vision-rcp.com')
                remote_url = f"{ui_base}?s={sid}&t={rtok}"
                
                click.secho("[+] Relay:    Connected", fg="blue")
                click.secho(f"    Session:  {sid}", fg="blue", bold=True)
                
                if not headless:
                    click.echo("\n[*] Scan to control remotely:\n")
                    qr_text = QRGenerator.to_terminal(remote_url)
                    click.echo(qr_text)
                    click.echo(f"\n[!] Join Link: {remote_url}\n")
            else:
                click.secho("[!] Relay:    Offline (Connection failed)", fg="yellow")
        
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
    """🚀 Start a remote-controlled Antigravity agent session.
    
    This is the all-in-one command that:
    
    \b
    1. Starts the Vision-RCP daemon
    2. Connects to the relay server
    3. Spawns the Antigravity agent via PTY
    4. Generates a QR code + join link
    5. Auto-opens the dashboard in your browser
    
    \b
    Examples:
      vision-rcp rcp
      vision-rcp rcp --workspace ./my-project
      vision-rcp rcp --local --no-browser
    """
    config = ctx.obj['config']
    device = ctx.obj['device']
    
    # Resolve workspace to absolute path
    workspace_path = os.path.abspath(workspace)
    
    # Apply overrides
    if relay_url: config.relay['url'] = relay_url
    if relay_token: config.relay['token'] = relay_token
    
    # Banner
    click.echo("")
    import sys
    click.secho("+-----------------------------------------------+", fg="cyan")
    click.secho("|                                               |", fg="cyan")
    click.secho("|      Vision RCP - Remote Agent Bridge         |", fg="cyan", bold=True)
    click.secho("|                                               |", fg="cyan")
    click.secho("+-----------------------------------------------+", fg="cyan")
    click.echo("")
    click.echo(f"  Machine:    {device.device_name}")
    click.echo(f"  Workspace:  {workspace_path}")
    click.echo(f"  Agent:      {agent}")
    click.echo(f"  Mode:       {'Local' if local else 'Relay'}")
    click.echo("")
    
    # Ensure device identity
    if not device.fingerprint:
        click.echo("[*] First run — initializing device identity...")
        data_dir = ctx.obj['data_dir']
        data_dir.mkdir(parents=True, exist_ok=True)
        device.init()
        click.secho("[OK] Device identity generated.", fg="green")
    
    # Build the daemon server
    server = RCPServer(config)
    
    async def run_rcp_session():
        # ── Step 0: Security TTL (24 Hour Window) ──────────────
        async def session_reaper(limit_secs: int):
            await asyncio.sleep(limit_secs)
            click.echo("")
            click.secho("!" * 50, fg="red")
            click.secho("  [!] 24-HOUR SECURITY WINDOW EXPIRED", fg="red", bold=True)
            click.secho("  Closing remote session for security.", fg="red")
            click.secho("!" * 50, fg="red")
            click.echo("")
            # Gracefully stop the server
            await uvicorn_server.shutdown()
            os._exit(0) # Force exit to ensure background tasks stop

        # Start the reaper
        asyncio.create_task(session_reaper(24 * 60 * 60))

        # ── Step 1: Start Uvicorn ──────────────────────────────
        click.echo("[1/5] Starting daemon...")
        
        cfg_uvicorn = uvicorn.Config(
            server.app,
            host=config.daemon['host'],
            port=config.daemon['port'],
            log_level="error",
        )
        uvicorn_server = uvicorn.Server(cfg_uvicorn)
        serve_task = asyncio.create_task(uvicorn_server.serve())
        
        while not uvicorn_server.started:
            await asyncio.sleep(0.1)
        
        # Get actual port
        actual_port = uvicorn_server.config.port
        if actual_port == 0 and uvicorn_server.servers:
            for sp in uvicorn_server.servers:
                for sock in sp.sockets:
                    actual_port = sock.getsockname()[1]
                    break
        
        server.set_port(actual_port)
        
        click.secho(f"      [OK] Daemon online (port {actual_port})", fg="green")
        click.echo(f"      Secret: {server.secret_key}")
        
        # ── Step 2: Connect to Relay ───────────────────────────
        session_id = None
        relay_access_token = None
        dashboard_url = None
        
        if not local and config.relay['url']:
            click.echo("[2/5] Connecting to relay...")
            
            wait_count = 0
            while wait_count < 30:
                if server._relay_client and server._relay_client.session_id:
                    break
                if wait_count % 5 == 0 and wait_count > 0:
                    click.echo(f"      ... still waiting for relay ({30 - wait_count}s left)")
                await asyncio.sleep(1)
                wait_count += 1
            
            if server._relay_client and server._relay_client.session_id:
                session_id = server._relay_client.session_id
                relay_access_token = server._relay_client.relay_token
                
                ui_base = config.daemon.get('ui_url', 'https://rcp.vision-rcp.com')
                dashboard_url = f"{ui_base}?s={session_id}&t={relay_access_token}&k={server.secret_key}&a={agent}"
                
                click.secho(f"      [OK] Relay authenticated", fg="green")
                click.secho(f"      Session: {session_id}", fg="blue", bold=True)
            else:
                click.secho("      [!] Relay offline — using local mode", fg="yellow")
                local_mode = True
        else:
            click.echo("[2/5] Skipping relay (local mode)")
        
        # ── Step 3: Auto-start Agent ───────────────────────────
        click.echo(f"[3/5] Spawning agent ({agent})...")
        
        # Build agent config — merge agents.toml with CLI overrides
        agent_config = {
            "working_dir": workspace_path,
        }
        
        # Load agents.toml config for this agent
        try:
            if sys.version_info >= (3, 11):
                import tomllib
            else:
                import tomli as tomllib
            
            agents_cfg_path = Path("agents.toml")
            if agents_cfg_path.exists():
                with open(agents_cfg_path, "rb") as f:
                    agents_data = tomllib.load(f)
                    # Try exact name first, then 'antigravity-agent' default
                    for key in [agent, "antigravity-agent"]:
                        if key in agents_data:
                            agent_config.update(agents_data[key])
                            break
        except Exception:
            pass
        
        # CLI command override
        if agent_cmd:
            agent_config["command"] = agent_cmd
        
        # Start the agent via handler
        try:
            from .models import LogEntry
            from .adapters import AdapterRegistry
            
            async def emit_callback(entry: LogEntry):
                # We echo to terminal so mirror_mode.py can scrape the port/status
                # and the user can see live mirrored output.
                color = "cyan" if entry.stream == "stderr" else None
                try:
                    click.secho(entry.data, fg=color)
                except UnicodeEncodeError:
                    # Fallback for terminals with limited charmaps
                    sanitized = entry.data.encode('ascii', errors='replace').decode('ascii')
                    click.secho(sanitized, fg=color)
                await server._stream_router.emit(entry)
            
            from .adapters import AdapterRegistry
            adapter = AdapterRegistry.get(agent, emit_callback)
            await adapter.start(agent_config)
            
            # Store in handler's active adapters
            if server._handler:
                server._handler._active_adapters[agent] = adapter
                # Start streaming task
                asyncio.create_task(adapter.stream_output())
            
            pid_str = getattr(adapter, "pid", "N/A")
            click.secho(f"      [OK] Agent spawned (PID: {pid_str})", fg="green")
        except Exception as e:
            click.secho(f"      [!] Agent spawn failed: {e}", fg="red")
            click.echo("      Dashboard will still work, start agent manually from UI")
        
        # ── Step 4: Access Info Retrieval ──────────────────────
        click.echo("[4/5] Generating access...")
        
        if dashboard_url:
            if not headless:
                click.echo("")
                click.secho("  +-------------------------------------+", fg="magenta")
                click.secho("  |   Scan QR to control from phone:    |", fg="magenta")
                click.secho("  +-------------------------------------+", fg="magenta")
                click.echo("")
                
                try:
                    qr_text = QRGenerator.to_terminal(dashboard_url)
                    click.echo(qr_text)
                except Exception:
                    click.echo("  (QR generation failed - use link below)")
                
                click.echo("")
                click.secho(f"  [+] Dashboard: {dashboard_url}", fg="cyan", bold=True)
                click.echo(f"  [+] Secret:    {server.secret_key}")
                click.echo("")
            else:
                # Still show basic link in headless
                click.secho(f"  [+] Dashboard: {dashboard_url}", fg="cyan", bold=True)
                click.echo(f"  [+] Secret:    {server.secret_key}")
        else:
            # Fallback to Local mode display
            ws_url = f"ws://localhost:{actual_port}/ws"
            ui_base = config.daemon.get('local_ui_url', 'http://localhost:5173')
            local_ui_url = f"{ui_base}?r={ws_url}&k={server.secret_key}&a={agent}"

            click.echo(f"  [+] Local:     {ws_url}")
            click.echo(f"  [+] Secret:    {server.secret_key}")
            click.secho(f"  [+] Dashboard: {local_ui_url}", fg="cyan", bold=True)
            dashboard_url = local_ui_url
        
        # ── Step 5: Auto-open Browser ──────────────────────────
        if not headless and not no_browser and dashboard_url:
            click.echo("[5/5] Opening dashboard...")
            try:
                webbrowser.open(dashboard_url)
                click.secho("      [OK] Browser opened", fg="green")
            except Exception:
                click.echo("      (Could not open browser automatically)")
        else:
            click.echo("[5/5] Skipping browser (headless/no-browser)")
        
        # ── Ready ──────────────────────────────────────────────
        click.echo("")
        click.secho("-" * 48, fg="green")
        click.secho("  [OK] Vision RCP is LIVE - Ready for commands", fg="green", bold=True)
        click.secho("-" * 48, fg="green")
        click.echo("")
        click.echo("  Send messages from the dashboard and they'll")
        click.echo("  be forwarded directly to your Antigravity agent.")
        click.echo("")
        click.echo("  Press Ctrl+C to stop the session.")
        click.echo("")
        
        # Wait for uvicorn to finish (blocks until Ctrl+C)
        await serve_task
    
    try:
        asyncio.run(run_rcp_session())
    except KeyboardInterrupt:
        click.echo("")
        click.secho("Stopping Vision-RCP session...", fg="yellow")
        click.echo("Agent terminated. Daemon stopped. Session ended.")
    except Exception as e:
        click.secho(f"\nFatal error: {e}", fg="red")
        import traceback
        traceback.print_exc()


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
