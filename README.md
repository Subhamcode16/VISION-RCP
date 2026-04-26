#  Vision-RCP: The Remote Control Plane for AI Agents

<div align="center">
  <p align="center">
    <strong>Mirror. Monitor. Mutate.</strong><br />
    The high-performance orchestration layer for local agents.
  </p>
  
  <p align="center">
    <img src="assets/dashboard.png" alt="Vision-RCP Dashboard" width="800" />
  </p>
</div>

---

## 🏗️ What is Vision-RCP?

Vision-RCP (Remote Control Plane) is a non-intrusive observation and orchestration layer designed to bridge the gap between **local AI agents** and **remote mobility**. 

Current AI agents (like Antigravity or VS-Code Copilot) are powerful but "session-locked." Vision-RCP breaks those chains by mirroring the agent's internal state, logs, and GUI permissions to a secure, web-accessible dashboard—allowing you to control your machine's AI from a mobile browser with **sub-50ms latency**.

---

## 🛡️ Key Features

- **🦾 Sentinel Agent**: An autonomous watchdog that handles "Run Command" permissions. It auto-approves safe operations (like `ls` or `git status`) while enforcing hard guardrails for destructive commands (`rm`, `del`).
- **🐚 Triple-Stream Architecture**: High-fidelity multiplexing of process output, system telemetry, and agent "thoughts" into a single, encrypted WebSocket stream.
- **🔗 Zero-Config Tunneling**: Access your local dashboard from anywhere in the world without opening ports or configuring complex VPNs, thanks to our outbound-only WSS relay.
- **🔍 Flow Audit**: A real-time traffic sniffer for inspecting raw RCP packets, ensuring your agents are behaving exactly as expected.
- **📐 Dependency-Aware DAG**: A topological process engine that ensures services start and stop in the correct order based on your project's architecture.

---

## 🧬 Triple-Stream Architecture

Vision-RCP operates on three distinct layers to ensure a native-like remote experience:

1.  **The Eyes (Ingestion)**: Kernel-level pipe-cloning and a "Universal Vacuum" scraper that reconstructs fragmented UI text into semantic messages.
2.  **The Voice (Command Layer)**: Secure, bi-directional authenticated communication using HMAC-SHA256 JWTs.
3.  **The Nervous System (Transport)**: A sub-50ms binary transport layer optimized for visual stability and real-time responsiveness.

---

## 🚀 Quick Start

### 1. Prerequisites
- Windows 10/11
- Python 3.10+
- Node.js (for local dashboard development)

### 2. Installation
Clone the repository and run the automated pairing script:
```powershell
git clone https://github.com/Subhamcode16/VISION-RCP.git
cd VISION-RCP
.\start-remote.bat
```

### 3. Pairing
1.  A QR code will appear in your terminal.
2.  Scan it with your mobile device.
3.  You are now in full control of your local AI agent from anywhere.

---

## 📜 Documentation & License

Vision-RCP is built for security and performance. For deep dives into the protocol and architecture, see our internal documentation (available upon request).

Licensed under [MIT License](LICENSE).
