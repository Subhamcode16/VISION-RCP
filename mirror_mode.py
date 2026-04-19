import subprocess
import sys
import re
import threading
import time
import os
import json

def stream_daemon_logs(pipe, port_event, url_event):
    """Monitor daemon output to capture bridge port and dashboard URL."""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    debug_log = open("mirror_debug.log", "w", encoding="utf-8")
    try:
        for line in iter(pipe.readline, ''):
            raw_line = line.strip()
            debug_log.write(f"RAW: {raw_line}\n")
            debug_log.flush()
            line = ansi_escape.sub('', raw_line)
            
            # Scrape Port
            if "BRIDGE_META: PORT=" in line:
                m = re.search(r"PORT=(\d+)", line)
                if m:
                    port_event['port'] = int(m.group(1))
                    port_event['ready'].set()
            
            # Scrape URL (Relay/Remote)
            if "Dashboard:" in line:
                m = re.search(r"Dashboard: (https?://\S+)", line)
                if m:
                    url_event['url'] = m.group(1)
                    url_event['mode'] = 'Relay'
                    url_event['ready'].set()
            
            # Scrape URL (Local)
            if "Local:" in line:
                m = re.search(r"Local: (ws?://\S+|http?://\S+)", line)
                if m:
                    url_event['url'] = m.group(1)
                    url_event['mode'] = 'Local'
                    url_event['ready'].set()

            # Pass through errors and warnings
            if "[ERROR]" in line or "Exception" in line or "Traceback" in line:
                print(f"  [!] Daemon: {line}")

            if "Relay offline" in line:
                url_event['relay_failed'] = True
            
            if "Secret:" in line:
                url_event['secret'] = line.split("Secret:")[1].strip()

    except Exception as e:
        print(f"Log scraper error: {e}")

def main():
    print("\n" + "="*50)
    print("      VISION-RCP MIRROR MODE (Stabilized)")
    print("="*50 + "\n")

    # Load Config
    config = {}
    config_path = "rcp_config.json"
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
            print(f"[*] Loaded config from {config_path}")
        except:
            print("[!] Warning: Could not parse rcp_config.json")

    # 1. Start Daemon
    cmd = [
        sys.executable, "-m", "daemon.src.cli", "rcp",
        "--agent", "bridge",
        "--headless",
        "--no-browser"
    ]
    
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"
    
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        env=env, bufsize=1, universal_newlines=True
    )
    
    port_event = {'ready': threading.Event(), 'port': None}
    url_event = {'ready': threading.Event(), 'url': None, 'secret': None, 'mode': 'Unknown', 'relay_failed': False}
    
    log_thread = threading.Thread(target=stream_daemon_logs, args=(proc.stdout, port_event, url_event), daemon=True)
    log_thread.start()
    
    print("[*] Waiting for Vision-RCP Daemon and Relay...")
    
    start_time = time.time()
    while time.time() - start_time < 30:
        if port_event['ready'].is_set() and url_event['ready'].is_set():
            break
        time.sleep(0.5)
    else:
        if not url_event['ready'].is_set():
            print("[-] Timeout waiting for Relay connection.")
            proc.terminate()
            return
        
        if url_event.get('relay_failed'):
            print("\n[!] ERROR: RELAY CONNECTION FAILED (Choice 2A Strict)")
            proc.terminate()
            return

    final_url = url_event['url']
    if url_event['mode'] == 'Relay' and "s=" in final_url:
        query = final_url.split("?")[1]
        final_url = f"http://localhost:5173?{query}"

    # Hardcode agent sync for bridge
    if "a=" not in final_url:
        sep = "&" if "?" in final_url else "?"
        final_url += f"{sep}a=bridge"

    print("\n" + "!"*50)
    print(f"  MIRROR MODE READY! ({url_event['mode']})")
    print(f"  Link: {final_url}")
    print("!"*50 + "\n")

    # 4. Start the Bridge Client
    try:
        bridge_cmd = [sys.executable, "daemon/src/mirror_bridge.py", str(port_event['port'])]
        
        # Add Workspace & Command from Config
        if config.get("workspace_path"):
            bridge_cmd += ["--cwd", config["workspace_path"]]
        
        if config.get("default_gate"):
            bridge_cmd += ["--gate"]
            
        if config.get("agent_command"):
            # If it's a string command, we keep it as list elements
            cmd_parts = config["agent_command"].split()
            bridge_cmd += cmd_parts
        
        # Run bridge
        subprocess.run(bridge_cmd)
    except KeyboardInterrupt:
        print("\n[*] Mirror stopped by user.")
    finally:
        proc.terminate()
        print("[*] Deamon shut down.")

if __name__ == "__main__":
    main()
