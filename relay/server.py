"""Vision-RCP Relay Server — Production-grade session registry & message router.

Architecture:
    Browser(s) ←→ Relay (Cloud) ←→ Daemon (Local Machine)
                (wss://)         (wss:// outbound)

The relay manages 'Sessions'. One session joins ONE daemon to MULTIPLE clients.
Message fan-out: Daemon messages are broadcast to all clients in the session.
"""

from __future__ import annotations

import asyncio
import json
import logging
import secrets
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from starlette.websockets import WebSocketState

from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(
    level=logging.WARNING, # Reduced to clear terminal for DB-PULSE
    format="%(asctime)s │ %(levelname)-7s │ %(name)-18s │ %(message)s",
)
logger = logging.getLogger("rcp.relay")

app = FastAPI(title="Vision-RCP Relay")

# Allow all origins for the bridge test
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SessionState(str, Enum):
    WAITING = "waiting"
    ACTIVE = "active"
    OFFLINE = "offline"
    EXPIRED = "expired"


@dataclass
class Session:
    session_id: str
    access_token: str
    device_fingerprint: str
    device_name: str
    daemon_ws: Optional[WebSocket] = None
    clients: List[WebSocket] = field(default_factory=list)
    state: SessionState = SessionState.WAITING
    created_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)

    @property
    def is_daemon_connected(self) -> bool:
        return self.daemon_ws is not None and self.daemon_ws.client_state == WebSocketState.CONNECTED


class SessionRegistry:
    def __init__(self):
        self._sessions: Dict[str, Session] = {}

    def create_session(self, fingerprint: str, name: str) -> Session:
        # Generate human-readable session ID (RCP-xxxx)
        while True:
            sid = f"RCP-{secrets.token_hex(2).upper()}"
            if sid not in self._sessions:
                break
        
        token = secrets.token_urlsafe(16)
        session = Session(
            session_id=sid,
            access_token=token,
            device_fingerprint=fingerprint,
            device_name=name
        )
        self._sessions[sid] = session
        logger.info(f"Created session {sid} for device {name}")
        return session

    def get_session(self, sid: str) -> Optional[Session]:
        return self._sessions.get(sid)

    def cleanup(self, max_age: float = 3600):
        """Remove sessions older than max_age (1 hour)."""
        now = time.time()
        to_remove = [sid for sid, s in self._sessions.items() 
                     if now - s.created_at > max_age and not s.is_daemon_connected]
        for sid in to_remove:
            del self._sessions[sid]
            logger.info(f"Cleaned up expired session {sid}")


registry = SessionRegistry()


@app.get("/health")
async def health():
    registry.cleanup()
    return {
        "status": "ok",
        "active_sessions": len(registry._sessions),
        "timestamp": time.time()
    }


import os
from dotenv import load_dotenv

load_dotenv()

# Static developer token (fallback for local dev)
# In production, set the RELAY_ACCESS_TOKEN environment variable.
DEV_TOKEN = os.getenv("RELAY_ACCESS_TOKEN", "VISION_DEV_TOKEN_CHANGE_ME")

@app.websocket("/ws/daemon")
async def daemon_endpoint(ws: WebSocket, 
                          token: str = Query(...),
                          fingerprint: str = Query(...), 
                          name: str = Query("unknown")):
    """Daemon registers here."""
    # Simple token check for now (production would use device signature)
    if token != DEV_TOKEN:
        await ws.close(code=4003, reason="Forbidden")
        return

    await ws.accept()
    
    session = registry.create_session(fingerprint, name)
    session.daemon_ws = ws
    session.state = SessionState.ACTIVE
    
    logger.info(f"Handshake complete: Session={session.session_id}, Token={session.access_token}")
    
    # Send handshake response
    await ws.send_json({
        "type": "handshake",
        "session_id": session.session_id,
        "token": session.access_token,
        "ts": time.time()
    })

    try:
        while True:
            # Receive from daemon
            data = await ws.receive_text()
            session.last_heartbeat = time.time()
            
            try:
                msg = json.loads(data)
                type_ = msg.get("type", "unknown")
                ref = msg.get("ref", "none")
                logger.info(f"[RELAY] [{session.session_id}] Daemon -> Relay: type={type_}, ref={ref}")
            except:
                pass

            # Fan-out to all clients
            dead_clients = []
            for client_ws in session.clients:
                try:
                    if client_ws.client_state == WebSocketState.CONNECTED:
                        await client_ws.send_text(data)
                except Exception:
                    dead_clients.append(client_ws)
            
            for dead in dead_clients:
                if dead in session.clients:
                    session.clients.remove(dead)
                    
    except WebSocketDisconnect:
        logger.info(f"Daemon {session.session_id} disconnected")
    finally:
        session.daemon_ws = None
        session.state = SessionState.OFFLINE


@app.websocket("/ws/client")
async def client_endpoint(ws: WebSocket, 
                          session_id: str = Query(...), 
                          token: str = Query(...)):
    """Client joins here."""
    origin = ws.headers.get("origin")
    logger.info(f"Client connection attempt: Session={session_id}, Origin={origin}")
    
    await ws.accept() # Accept first to avoid handshake 403s
    
    session = registry.get_session(session_id)
    if not session:
        logger.warning(f"Session {session_id} not found in registry (Total sessions: {len(registry._sessions)})")
        await ws.close(code=4001, reason="Session not found")
        return
        
    if session.access_token != token:
        logger.warning(f"Token mismatch for {session_id}: expected {session.access_token}, got {token}")
        await ws.close(code=4001, reason="Invalid token")
        return

    logger.info(f"Client authenticated: Session={session_id}")
    session.clients.append(ws)
    logger.info(f"Client joined session {session_id}")

    try:
        while True:
            # Receive from client
            data = await ws.receive_text()
            
            try:
                msg = json.loads(data)
                type_ = msg.get("type", "unknown")
                id_ = msg.get("id", "none")
                logger.info(f"[RELAY] [{session_id}] Client -> Relay: type={type_}, id={id_}")
            except:
                pass

            # Forward to daemon
            if session.is_daemon_connected:
                try:
                    await session.daemon_ws.send_text(data)
                except Exception as e:
                    logger.warning(f"Failed to forward to daemon in {session_id}: {e}")
            else:
                await ws.send_json({
                    "type": "error",
                    "error": {"code": "OFFLINE", "message": "Daemon is offline"}
                })
                
    except WebSocketDisconnect:
        logger.info(f"Client left session {session_id}")
    finally:
        if ws in session.clients:
            session.clients.remove(ws)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
