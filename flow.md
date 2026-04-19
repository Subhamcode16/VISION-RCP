# Vision RCP — CLI UX, Session Flow & QR System Design

---

## 🧠 Core Philosophy

**Zero friction. One command. Instant control.**

The system should feel:

* effortless to install
* instant to start
* seamless to connect

> Run → Scan → Control

---

# ⚙️ CLI Command Design

## 🔥 Primary Command

```bash
vision-rcp <command> [options]
```

---

## 🧩 Core Commands

### 1. Initialize (One-Time Setup)

```bash
vision-rcp init
```

**Responsibilities:**

* Create config file: `~/.vision-rcp/config.toml`
* Generate device identity
* Install/start background daemon
* Validate dependencies

---

### 2. Start Session (Core Command)

```bash
vision-rcp start
```

#### Options:

```bash
vision-rcp start --name dev-stack
vision-rcp start --tunnel
vision-rcp start --relay https://rcp.app
vision-rcp start --headless
```

---

### 3. Status

```bash
vision-rcp status
```

---

### 4. Stop

```bash
vision-rcp stop
```

---

### 5. Session Management

```bash
vision-rcp sessions
vision-rcp attach <id>
vision-rcp kill <id>
```

---

# 🚀 Session Start Flow

## 🔥 User Command

```bash
vision-rcp start
```

---

## 🧠 Internal Execution Flow

```text
1. Ensure daemon is running
2. Create new session
3. Initialize transport:
   - Tunnel (ngrok/bore) OR
   - Cloud relay
4. Generate:
   - session_id
   - short-lived access token
5. Construct connection URL
6. Generate QR code
7. Begin real-time streaming
```

---

## 💻 CLI Output (User Experience)

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Vision RCP — Remote Control Ready
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📦 Session: dev-stack
🖥 Machine: user-device
🟢 Status: Online

🌐 Mode: Tunnel (ngrok)
🔗 URL: https://abc123.ngrok-free.app/s/dev-stack

📱 Scan to connect:

   ███████████████████████████
   █ ▄▄▄▄▄ █ ▄ █▀▄█ ▄▄▄▄▄ █
   █ █   █ █▀▀▀█ ▀█ █   █ █
   █ █▄▄▄█ █ ▄▀█▀▄█ █▄▄▄█ █
   █▄▄▄▄▄▄▄█▄█▄█▄█▄█▄▄▄▄▄▄▄█

🔑 Token: expires in 10 min

⚡ Commands:
  [Ctrl+C] → Stop session
  [r]      → Restart session
  [o]      → Open in browser

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

# 📱 QR System Design

## 🧠 QR Payload Structure

QR should encode structured data:

```json
{
  "url": "https://rcp.app/s/abc123",
  "token": "short-lived-token",
  "device_hint": "user-device"
}
```

---

## 🔐 Security Design

* Token expiry: 5–10 minutes
* Optional single-use tokens
* Scoped to session
* No persistent credentials inside QR

---

## 📲 Connection Flow (Mobile)

1. User scans QR
2. Browser opens automatically
3. Token authenticates session
4. WebSocket connection established
5. Terminal/control UI loads instantly

---

# 🔄 Connection Modes

---

## 🟢 Tunnel Mode (MVP)

```bash
vision-rcp start --tunnel
```

* Auto-starts ngrok/bore
* Generates public URL
* No backend required

---

## 🔵 Relay Mode (Production)

```bash
vision-rcp start --relay
```

* Connects to persistent cloud relay
* Enables multi-device sync
* Stable long-lived sessions

---

## 🟡 Local Mode (Debugging)

```bash
vision-rcp start --local
```

* Runs on localhost only
* No external access

---

# 🧠 Slash Command Integration

---

## Inside Agent (Claude/Codex/Terminal Agent)

User input:

```text
/rcp start
```

---

## Execution Flow

Agent executes:

```bash
vision-rcp start
```

---

## Result

* CLI output is shown inside agent terminal
* QR + URL available immediately
* Feels like native agent feature

---

# ⚙️ Configuration Design (TOML)

```toml
[daemon]
auto_start = true
name = "user-device"

[network]
default_mode = "tunnel"

[security]
require_approval = true
token_expiry_minutes = 10

[ui]
open_browser_on_start = false
```

---

# 🧠 Daemon Behavior

On session start:

```text
- Register session
- Establish outbound connection
- Attach to process manager
- Start streaming logs
- Listen for remote control commands
```

---

# ⚡ Developer Experience Goals

---

## ✅ Zero Configuration

```bash
npx vision-rcp start
```

---

## ✅ Instant Feedback

* Logs stream immediately
* No waiting or buffering

---

## ✅ Minimal Authentication Friction

* Temporary token-based access
* No mandatory login (initially)

---

## ✅ Universal Compatibility

Works with:

* terminal environments
* VS Code
* Claude Code
* Codex CLI
* any shell-based agent

---

# 🚨 Anti-Patterns to Avoid

---

## ❌ Do NOT require users to:

* configure ports
* manage domains
* understand networking

---

## ❌ Do NOT introduce multi-step flows:

* login → config → connect → start → scan

---

## ✅ Ideal Flow:

```text
start → scan → control
```

---

# 🧠 Final User Journey

```text
1. Install:
   npx vision-rcp init

2. Start:
   vision-rcp start

3. View QR code

4. Scan from phone

5. Control system instantly
```

---

# 🚀 Summary

This design ensures:

* ultra-fast onboarding
* minimal cognitive load
* powerful remote control capability
* compatibility with any local agent system

---

**End of Document**
