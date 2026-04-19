# Vision-RCP Architecture

## System Topology

```
┌──────────────────┐     ┌───────────────────────┐     ┌──────────────────┐
│   Browser Client  │────▶│   Relay Server (Cloud)│◀────│  Daemon (Local)  │
│   React + xterm   │ wss │   FastAPI + WS Bridge │ wss │  FastAPI + WS    │
│   port: N/A       │     │   port: 8080          │     │  port: random    │
└──────────────────┘     └───────────────────────┘     └──────────────────┘
                              │                              │
                              │ Serves static UI             │ Manages processes
                              │ Forwards messages            │ Runs DAG engine
                              │ Channel matching             │ Streams stdout/err
                              │                              │ Auth + Audit
```

## Data Flow

### Local Mode (Direct)
```
Browser ←→ ws://localhost:PORT/ws ←→ Daemon
```

### Remote Mode (Via Relay)
```
Browser ←→ wss://relay.domain/ws/client?token=T ←→ Relay ←→ wss://relay.domain/ws/daemon?token=T ←→ Daemon
```
The daemon connects OUTBOUND to the relay. No inbound ports exposed.

## Protocol: RCP Envelope

Every message follows the same envelope shape:
```json
{
  "id": "uuid",
  "type": "command | response | stream | error | heartbeat",
  "ts": "ISO-8601",
  "token": "jwt-access-token",
  "command": "process.spawn | process.kill | ...",
  "ref": "uuid-of-original-command",
  "payload": {},
  "error": { "code": "...", "message": "..." }
}
```

## Security Model (Zero-Trust)

1. **First Launch**: Daemon generates a random secret key → displayed once in terminal
2. **Login**: Client sends `auth.login { secret }` → Daemon validates → Issues JWT
3. **All Commands**: Must include valid JWT in `token` field
4. **Tokens**: Short-lived access (15min) + Long-lived refresh (7 days)
5. **Refresh Rotation**: Old refresh token is revoked on each refresh
6. **Rate Limiting**: Token bucket per-connection (60 cmd/min, 5 auth/min)
7. **Audit Trail**: Every action logged to SQLite with timestamp, IP, result
8. **Relay Auth**: Separate RELAY_TOKEN for daemon↔relay authentication

## Process Lifecycle

```
PENDING → STARTING → RUNNING ←→ RESTARTING
                         ↓
                    STOPPING → STOPPED
                         ↓
                       FAILED → (auto-restart if enabled)
```

## Dependency Graph Engine

Uses `graphlib.TopologicalSorter` for:
- Cycle detection at registration time
- Parallel-ready startup (independent processes start concurrently)
- Reverse-order shutdown (dependents stop first)
- Dependency health waiting (wait up to 30s for deps to reach RUNNING)

## Directory Structure

```
Vision-RCP/
├── daemon/                    # Python daemon (runs on local machine)
│   ├── config.toml            # TOML configuration
│   ├── requirements.txt       # Python dependencies
│   └── src/
│       ├── __init__.py
│       ├── main.py            # Entry point (port binding, banner)
│       ├── server.py          # WebSocket server (FastAPI)
│       ├── protocol.py        # Message envelope + types
│       ├── models.py          # Data models (process, group, system)
│       ├── config.py          # TOML config loader
│       ├── handlers.py        # Command routing (all 15 commands)
│       ├── process_manager.py # Process lifecycle (spawn/kill/restart)
│       ├── stream_router.py   # stdout/stderr fan-out to clients
│       ├── dependency_graph.py# DAG engine with topological sort
│       ├── relay_connector.py # Outbound bridge to relay
│       └── security/
│           ├── __init__.py
│           ├── auth.py        # JWT issuer/validator
│           ├── audit.py       # SQLite audit logger
│           └── rate_limiter.py# Token bucket rate limiting
│
├── relay/                     # Custom relay server (deploy to cloud)
│   ├── requirements.txt
│   └── server.py              # WebSocket bridge + static file server
│
├── ui/                        # React streaming UI
│   ├── package.json
│   ├── vite.config.ts
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── index.css          # Design system tokens
│       ├── lib/
│       │   ├── protocol.ts    # Protocol types (mirrors Python)
│       │   └── store.ts       # Zustand global state
│       ├── hooks/
│       │   └── useRCP.ts      # WebSocket hook + auto-reconnect
│       └── components/
│           ├── AuthGate.tsx    # Login screen
│           ├── Layout.tsx      # 3-panel grid
│           ├── ProcessList.tsx # Live process table
│           ├── Terminal.tsx    # xterm.js wrapper
│           └── StatusBar.tsx   # System metrics bar
│
├── protocol/
│   └── rcp.schema.json        # JSON Schema for the protocol
│
├── start-app.bat              # One-click launcher
└── .gitignore
```
