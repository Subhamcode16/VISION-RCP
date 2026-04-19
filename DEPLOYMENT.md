# Vision-RCP Deployment Guide (Cloud & Mobile)

This guide details how to move Vision-RCP from `localhost` to a production-grade cloud environment, enabling remote and mobile access.

## High-Level Architecture
1.  **Dashboard (UI)**: Deployed to **Vercel**.
2.  **Relay (Bridge)**: Hosted on your local machine and exposed via **Cloudflare Tunnel** (or deployed to Render).
3.  **Daemon (Local)**: Connects to the Relay and receives commands from the UI.

---

## 1. Dashboard Deployment (Vercel)

The frontend is a Vite/React application. Vercel is the recommended host.

1.  **Push your code** to a GitHub repository.
2.  **Import the project** in the [Vercel Dashboard](https://vercel.com/new).
3.  **Configure Environment Variables**:
    - Under "Environment Variables", add:
      - `VITE_RELAY_WS_URL` = `wss://your-relay-tunnel.com/client` (We will generate this in Step 2).
4.  **Deploy**. Vercel will give you a public URL (e.g., `https://vision-rcp.vercel.app`).

---

## 2. Relay Exposer (Cloudflare Tunnel)

To allow the Vercel Dashboard to talk to your local Relay without port-forwarding, use `cloudflared`.

1.  **Install Cloudflare Tunnel**: [Instructions here](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/install-and-setup/tunnel-guide/local/).
2.  **Run the Relay locally**:
    ```bash
    python -m relay.server
    ```
3.  **Create the Tunnel**:
    ```bash
    cloudflared tunnel --url http://localhost:8080
    ```
4.  **Capture the Tunnel URL**: Cloudflare will provide a `.trycloudflare.com` URL.
    - Example: `https://gentle-ocean-123.trycloudflare.com`
5.  **Update Vercel**: Use `wss://gentle-ocean-123.trycloudflare.com/ws/client` as your `VITE_RELAY_WS_URL`.

---

## 3. Daemon Configuration

To activate "Mobile Mode", the Daemon must be aware of your public Dashboard URL.

1.  **Create/Update `.env`** in the `daemon/` directory (or set system env vars):
    ```env
    VITE_DASHBOARD_URL=https://vision-rcp.vercel.app
    RELAY_URL=https://gentle-ocean-123.trycloudflare.com
    RELAY_TOKEN=VISION_DEV_TOKEN_CHANGE_ME
    ```
2.  **Launch Daemon**:
    ```bash
    python -m src.main
    ```
3.  **Mobile Access**:
    - The Daemon will print a **QR Code** in the terminal.
    - Scan it with your phone. It will automatically open the Vercel dashboard and perform a handshake with your local machine.

---

## Security Best Practices
- **Token Rotation**: New session IDs are generated every time the Daemon restarts.
- **WSS Encryption**: Cloudflare and Vercel provide end-to-end TLS encryption.
- **Local Secret**: Even if someone finds your Relay URL, they cannot control your machine without the `secret_key` stored locally on your disk.

---

## Troubleshooting
- **CORS Error**: Ensure the Relay server has `allow_origins=["*"]` during the initial setup (this is the default in current code).
- **Handshake Timeout**: Check that your internet connection is stable and the `cloudflared` tunnel is still active.
