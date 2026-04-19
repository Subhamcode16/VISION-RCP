# Vision-RCP: Agent Memory & Learning Log

This file contains critical insights and "gotchas" discovered during development to prevent future agents from repeating mistakes.

## 1. Relay Connection Bottlenecks
**Issue**: Using a static `connection_id` for relay-sourced commands.
**Learning**: In a bridge/relay architecture, the daemon treats the relay as a single connection, but it's actually a proxy for multiple clients.
- **Mistake**: Assigning `connection_id=999` to all relay commands.
- **Consequence**: Multiple browser tabs quickly exhaust the daemon's rate-limit bucket (capacity 10), causing `auth.login` and streams to stall/timeout.
- **Solution**: Use session-prefixed IDs (e.g., `relay:SESSION_ID`) and implement "Relay Buckets" in the `RateLimiter` with significantly higher capacity (10x burst).

## 2. Tunnel Connection Stability (Bore/Ngrok)
**Issue**: Tunnels closing idle WebSocket connections.
**Learning**: Tunnels like `bore` are extremely sensitive to inactivity and lack of keep-alive.
- **Mistake**: Relying on default WebSocket ping intervals (20s+).
- **Consequence**: The daemon silently loses physical connectivity to the relay, while the relay still thinks the session is active.
- **Solution**: Implement aggressive pings (`ping_interval=10`) and fail-fast handshake timeouts (5s max) in the `RelayClient`.

## 3. UI Command Timeouts
**Issue**: 15-second timeout for generic commands.
**Learning**: Bridge mode adds 4 network legs: Browser → Relay → Tunnel → Daemon → Tunnel → Relay → Browser.
- **Mistake**: Using a 15s timeout for `auth.login`.
- **Consequence**: Slow tunnel cold-starts or network jitter cause the UI to reject the login even if the daemon successfully processed it.
- **Solution**: Set `COMMAND_TIMEOUT` to at least 30s when bridge mode is detected or as a default to handle peak latency.

## 5. Relay Session Tokens (Client Handshake)
**Issue**: Browser client unable to join relay session despite knowing the Session ID.
**Learning**: The relay generates a unique `access_token` for each daemon session. This is *not* the same as the daemon's static `VISION_DEV_TOKEN`.
- **Mistake**: UI trying to connect using the static daemon token or no token.
- **Consequence**: Handshake failure with `Invalid Token (4001)`.
- **Solution**: The daemon must log the **Session Token** received during its handshake so the operator can provide it to the UI (e.g., via query params `?s=ID&t=TOKEN`).
- **Debugging Tip**: If `getaddrinfo failed` occurs for a cloud relay, fallback to a local relay server (`python -m relay.server`) and update `config.toml` to `ws://127.0.0.1:8080`.
