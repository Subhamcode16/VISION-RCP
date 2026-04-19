import sys
import os

# Add daemon/src to path for imports
sys.path.append(os.path.join(os.getcwd(), 'daemon'))

try:
    from daemon.src.adapters.antigravity import AntigravityAdapter
    print("[*] Successfully imported AntigravityAdapter")
except Exception as e:
    print(f"[!] Import failed: {e}")
    sys.exit(1)

async def test_init():
    def dummy_emit(msg):
        print(f"  [LOG]: {msg.content}")

    adapter = AntigravityAdapter("antigravity", dummy_emit)
    config = {
        "project_path": os.path.abspath("C:/Users/User/OneDrive/Desktop/PERSONAL/antigravity")
    }
    
    print("[*] Starting adapter...")
    await adapter.start(config)
    
    print(f"[*] SDK Available: {adapter.agent is not None}")
    
    if adapter.agent:
        print("[*] Sending test message 'hello'...")
        await adapter.send_message("hello")
    else:
        print("[!] SDK not available, skipping message test.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_init())
