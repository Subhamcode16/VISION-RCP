# Vision-RCP Tech Stack

## Daemon (Local Machine)
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Runtime | Python | 3.11+ | Async subprocess management |
| Framework | FastAPI | 0.115+ | WebSocket server |
| ASGI | Uvicorn | 0.32+ | HTTP/WS server |
| WebSocket | websockets | 13+ | WS client (relay connector) |
| Validation | Pydantic | 2.9+ | Message validation |
| Process Monitor | psutil | 6.1+ | CPU, memory, health checks |
| Auth | PyJWT | 2.9+ | JWT issuance & validation |
| Crypto | cryptography | 43+ | Key generation utilities |
| Database | aiosqlite | 0.20+ | Async SQLite audit logging |
| Config | tomllib | stdlib | TOML configuration |
| DAG | graphlib | stdlib | Topological sort for deps |

## Relay Server (Cloud)
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Framework | FastAPI | 0.115+ | WebSocket bridge + static server |
| ASGI | Uvicorn | 0.32+ | HTTP/WS server |
| WebSocket | websockets | 13+ | Bidirectional message forwarding |

## UI (Browser)
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Framework | React | 19 | Component rendering |
| Language | TypeScript | 5.6 | Type safety |
| Build | Vite | 6 | Dev server + production build |
| Terminal | @xterm/xterm | 5.5 | Terminal emulator |
| State | Zustand | 5 | Global state management |
| Graphs | D3.js | 7.9 | DAG visualization |
| Fonts | JetBrains Mono + Inter | latest | Mono + UI typography |

## Infrastructure
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Port | Dynamic (port 0) | OS assigns random free port |
| Tunnel | Custom Relay | No third-party tunnel required |
| Config | TOML | Human-readable configuration |
| Storage | ~/.vision-rcp/ | Secrets, audit DB, port file |
| Protocol | JSON over WebSocket | Structured RCP envelope |
| Auth | HMAC-SHA256 JWT | Zero-trust token auth |
| Audit | SQLite | Persistent security event log |

## Security Stack
| Layer | Implementation |
|-------|---------------|
| Transport | Encrypted WebSocket (wss://) via relay |
| Authentication | HMAC-signed JWT (HS256) |
| Secret Storage | File-based (0600 permissions) |
| Token Lifecycle | 15min access, 7-day refresh, rotation |
| Brute Force | Token bucket (5 auth attempts/min) |
| Command Rate | Token bucket (60 commands/min) |
| Audit | SQLite with 30-day retention |
| Secret Comparison | Constant-time (hmac.compare_digest) |
