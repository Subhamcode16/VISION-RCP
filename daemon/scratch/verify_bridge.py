import asyncio
import logging
from daemon.src.adapters.antigravity import AntigravityAdapter

# Configure logging to see the bridge action
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

async def test_bridge():
    print("\n--- Antigravity Bridge Verification ---")
    
    # Mock emit callback
    async def mock_emit(msg):
        if not msg.data.startswith("["): # Ignore internal logs
            print(f"[{msg.name.upper()}] >>> {msg.data}")

    adapter = AntigravityAdapter("test", mock_emit)
    
    print("[*] Starting adapter...")
    await adapter.start({})
    
    # Wait for connection and snapshot
    print("[*] Waiting for connection and snapshot (5s)...")
    print("    (Please make sure Antigravity chat is open on your screen)")
    
    # Give it time to find window and bootstrap
    for _ in range(30):
        if adapter.is_bootstrapped:
            break
        await asyncio.sleep(0.5)

    if not adapter.is_bootstrapped:
        print("[!] Failed to bootstrap scraper. Is the window open?")
        return

    print("\n[ACTIVE] Monitoring for NEW responses...")
    print("        Try typing something in Antigravity or sending from the dashboard.")
    print("        Monitoring for 30 seconds... (Ctrl+C to stop early)\n")
    
    try:
        await asyncio.sleep(30)
    except KeyboardInterrupt:
        pass
    finally:
        await adapter.stop()
        print("\n--- Verification Finished ---\n")

if __name__ == "__main__":
    try:
        asyncio.run(test_bridge())
    except KeyboardInterrupt:
        pass
