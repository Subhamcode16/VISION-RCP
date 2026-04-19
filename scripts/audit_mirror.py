import asyncio
import sys
import os
import logging
from pathlib import Path

# Add current directory to path to handle daemon as a package
sys.path.append(os.getcwd())

from daemon.src.adapters.bridge import SocketBridgeAdapter
from daemon.src.models import LogEntry

# Configure audit logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("audit_mirror.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("rcp.audit")

async def mock_emit_callback(entry: LogEntry):
    """Log all agent output to the audit log."""
    logger.info(f"[FROM BRIDGE -> UI] {entry.data}")

async def run_audit():
    logger.info("Starting Vision-RCP Connection Audit...")
    logger.info("---------------------------------------")

    # 1. Initialize Adapter
    adapter = SocketBridgeAdapter(name="audit-agent", emit_callback=mock_emit_callback)
    
    # 2. Start Adapter
    logger.info("[1/3] Starting SocketBridgeAdapter...")
    await adapter.start({"working_dir": "."})
    port = adapter.port
    logger.info(f"[*] Adapter is listening on 127.0.0.1:{port}")

    # 3. Start Streaming Task
    asyncio.create_task(adapter.stream_output())

    logger.info("[2/3] Waiting for bridge client (mirror_bridge.py) to connect...")
    logger.info(f"      To connect, run: python daemon/src/mirror_bridge.py {port}")
    
    # Give the user some time or wait for connection
    while not adapter._connected.is_set():
        await asyncio.sleep(0.5)
    
    logger.info("[OK] Bridge Client Connected!")
    logger.info("---------------------------------------")
    logger.info("[3/3] Interactive Test Loop Start")
    logger.info("Type messages to send to the 'Agent Panel'. Type 'exit' to stop.")

    try:
        while True:
            # We use a non-blocking input simulation for audit
            user_msg = await asyncio.get_event_loop().run_in_executor(None, input, "DASHBOARD > ")
            
            if user_msg.lower() == 'exit':
                break
                
            logger.info(f"[FROM UI -> BRIDGE] {user_msg}")
            await adapter.send_message(user_msg)
            
            # Allow some time for the echo back if using a real agent
            await asyncio.sleep(0.1)

    except KeyboardInterrupt:
        pass
    finally:
        logger.info("Stopping Audit...")
        await adapter.stop()
        logger.info("Audit log saved to audit_mirror.log")

if __name__ == "__main__":
    asyncio.run(run_audit())
