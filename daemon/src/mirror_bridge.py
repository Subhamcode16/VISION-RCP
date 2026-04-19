import socket
import sys
import threading
import time
import subprocess
import os
import re

# Windows-specific for non-blocking key hits
if os.name == 'nt':
    import msvcrt
else:
    msvcrt = None

# Global state for Gating
GATED_MODE = False
MODE_LOCK = threading.Lock()

def clean_text(text):
    """Strip ANSI codes and noise for the dashboard."""
    # Strip ANSI
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    cleaned = ansi_escape.sub('', text)
    # Remove redundant carriage returns and leading/trailing whitespace
    return cleaned.replace('\r', '').strip()

def socket_to_stream(sock, target_stream, proc=None):
    """Receive data from daemon and forward to target_stream (stdout or stdin of proc)."""
    global GATED_MODE
    try:
        while True:
            data = sock.recv(4096)
            if not data:
                break
            
            raw_msg = data.decode('utf-8')
            for msg in raw_msg.split('\n'):
                if not msg: continue
                
                if msg == "__INTERRUPT__":
                    if proc:
                        print("\n[REMOTE INTERRUPT] Sending SIGINT...", file=sys.stderr)
                        import signal
                        if os.name == 'nt':
                            proc.send_signal(signal.CTRL_C_EVENT)
                        else:
                            proc.send_signal(signal.SIGINT)
                    else:
                        print("\n\n[REMOTE INTERRUPT RECEIVED]\n", file=sys.stderr, flush=True)
                elif msg.startswith("__APPROVAL__"):
                    pass
                elif msg == "--- ACK ---":
                    continue
                else:
                    # Gating Logic
                    with MODE_LOCK:
                        is_gated = GATED_MODE
                    
                    if is_gated:
                        print(f"\n[PENDING APPROVE] Dashboard: \"{msg}\"")
                        print("Forward to agent? (y/n): ", end='', flush=True)
                        
                        # Wait for local terminal input
                        choice = sys.stdin.readline().strip().lower()
                        if choice != 'y':
                            print("[DENIED] Message dropped.", flush=True)
                            continue
                        print("[APPROVED] Forwarding...", flush=True)

                    # Forward to child process stdin
                    if proc:
                        target_stream.write((msg + "\n").encode('utf-8'))
                        target_stream.flush()
                    else:
                        print(f"\n[Dashboard]: {msg}", flush=True)
    except Exception as e:
        if proc and proc.poll() is not None:
            return
        print(f"\n[Bridge Read Error: {e}]\n", file=sys.stderr, flush=True)

def stream_to_socket(source_stream, sock, label="Terminal", clean=False):
    """Read data from source_stream and send to daemon socket."""
    try:
        if hasattr(source_stream, 'readline'):
            # Determine sentinel: b'' for binary streams, '' for text.
            # subprocess pipes are binary by default; sys.stdin is text.
            is_binary = True
            if hasattr(source_stream, 'mode'):
                is_binary = 'b' in source_stream.mode
            elif hasattr(source_stream, 'encoding'):
                # sys.stdin/stdout usually have an encoding attribute
                is_binary = False
            
            sentinel = b'' if is_binary else ''
            
            for line in iter(source_stream.readline, sentinel):
                if not line: break
                
                # Convert bytes to string for cleaning if needed
                out_data = line
                if clean:
                    text = line.decode('utf-8', errors='ignore') if isinstance(line, bytes) else line
                    text = clean_text(text)
                    if not text: continue # Drop empty/noise lines
                    out_data = (text + "\n").encode('utf-8')
                
                # Send
                if isinstance(out_data, bytes):
                    sock.sendall(out_data)
                else:
                    sock.sendall(out_data.encode('utf-8'))
        else:
            for line in source_stream:
                if not line: break
                sock.sendall(line.encode('utf-8'))
    except Exception as e:
        print(f"\n[Bridge Write Error ({label}): {e}]\n", file=sys.stderr)

def main():
    global GATED_MODE
    if len(sys.argv) < 2:
        print("Usage: python mirror_bridge.py <port> [--cwd <path>] [--gate] [command...]")
        sys.exit(1)

    port = int(sys.argv[1])
    
    # Parse Args
    args = sys.argv[2:]
    cwd = None
    if '--cwd' in args:
        idx = args.index('--cwd')
        cwd = args[idx+1]
        args = args[:idx] + args[idx+2:]
    
    if '--gate' in args:
        GATED_MODE = True
        args.remove('--gate')
        
    command = args
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print(f"[*] Connecting to Vision-RCP Bridge on port {port}...")
    
    for _ in range(5):
        try:
            sock.connect(('127.0.0.1', port))
            break
        except ConnectionRefusedError:
            time.sleep(0.5)
    else:
        print("[-] Could not connect to bridge.")
        sys.exit(1)

    proc = None
    if command:
        print(f"[*] Spawning agent: {' '.join(command)}")
        if cwd: print(f"[*] Workspace: {cwd}")
        
        # Use shell=True for .cmd files if needed, or stick to list
        # For Antigravity, we'll try binary direct list first
        proc = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=cwd,
            bufsize=0
        )
        print(f"[+] Agent spawned (PID: {proc.pid})")
        
        t1 = threading.Thread(target=socket_to_stream, args=(sock, proc.stdin, proc), daemon=True)
        t2 = threading.Thread(target=stream_to_socket, args=(proc.stdout, sock, "Agent", True), daemon=True)
    else:
        print("[+] Mirror active (Standard Terminal mode).")
        t1 = threading.Thread(target=socket_to_stream, args=(sock, sys.stdout), daemon=True)
        t2 = threading.Thread(target=stream_to_socket, args=(sys.stdin, sock, "Terminal"), daemon=True)
    
    t1.start()
    t2.start()
    
    print("-" * 50)
    print(f"--- BRIDGE START [GATE: {'ON' if GATED_MODE else 'OFF'}] ---")
    print(" (Press 'G' to toggle manual approval gate)")
    print("-" * 50, flush=True)
    
    try:
        while t1.is_alive() and t2.is_alive():
            if proc and proc.poll() is not None:
                print(f"\n[*] Agent process exited with code {proc.returncode}")
                break
            
            # Non-blocking toggle check
            if msvcrt and msvcrt.kbhit():
                key = msvcrt.getch().decode('utf-8').lower()
                if key == 'g':
                    with MODE_LOCK:
                        GATED_MODE = not GATED_MODE
                        print(f"\n[MODE] Gate is now {'ENABLED' if GATED_MODE else 'DISABLED (Pure Pipe)'}", flush=True)
            
            time.sleep(0.1) # Faster response for keyboard
    except KeyboardInterrupt:
        if proc: proc.terminate()
    
    print("[*] Mirror bridge stopped.")

if __name__ == "__main__":
    main()
