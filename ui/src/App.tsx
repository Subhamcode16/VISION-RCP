import { useEffect, useState } from 'react';
import { useRCP } from './hooks/useRCP';
import { useStore } from './lib/store';
import { AuthGate } from './components/AuthGate';
import { Layout } from './components/Layout';
import { AgentChat } from './components/AgentChat';
import { Sidebar } from './components/Sidebar';
import { StatusBar } from './components/StatusBar';
import { Toaster } from './components/Toaster';
import { FlowAudit } from './components/FlowAudit';
import { Terminal as ProcessTerminal } from './components/Terminal';

// Default to local WebSocket or Relay WebSocket
const LOCAL_WS = 'ws://localhost:9077/ws';
const RELAY_WS = import.meta.env.VITE_RELAY_WS_URL || (window.location.hostname === 'localhost' ? 'ws://localhost:8080/ws/client' : 'wss://relay.vision-rcp.com/ws/client');

// Helper to get initial params synchronously to avoid 9077 race
function getInitialParams() {
  const urlParams = new URLSearchParams(window.location.search);
  const s = urlParams.get('s') || urlParams.get('sid');
  const t = urlParams.get('t') || urlParams.get('token');
  const r = urlParams.get('r') || urlParams.get('relay');
  const k = urlParams.get('k') || urlParams.get('key');

  if (s || t || r || k) {
    return {
      sessionId: (s || undefined)?.trim(),
      relayToken: (t || undefined)?.trim(),
      customRelay: (r || undefined)?.trim(),
      secretKey: (k || undefined)?.trim()?.replace(/\|$/, ''), // Strip trailing pipe from ASCII banners
      agentName: (urlParams.get('a') || urlParams.get('agent') || undefined)?.trim()
    };
  }

  const stored = localStorage.getItem('vision_rcp_session');
  if (stored) {
    try {
      return JSON.parse(stored);
    } catch {
      return {};
    }
  }
  return {};
}

function App() {
  const { auth, connectionStatus, activeTab } = useStore();
  const [sessionParams] = useState(getInitialParams());

  // Effect handles side-effects like cleaning URL or updating storage
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const s = urlParams.get('s');
    const t = urlParams.get('t');
    const r = urlParams.get('r');
    const k = urlParams.get('k');
    const a = urlParams.get('a');

    if (s || t || r || k || a) {
      localStorage.setItem('vision_rcp_session', JSON.stringify(sessionParams));
      // Clean URL without refreshing
      const cleanUrl = window.location.origin + window.location.pathname;
      window.history.replaceState({}, document.title, cleanUrl);
    }
  }, [sessionParams]);

  const { sessionId, relayToken, customRelay, secretKey, agentName } = sessionParams;

  useEffect(() => {
    if (agentName) {
      useStore.getState().setActiveAdapter(agentName);
    }
  }, [agentName]);
  
  let wsUrl = (sessionId ? RELAY_WS : LOCAL_WS);
  
  // Sanitize custom relay (r param)
  if (customRelay) {
    if (/^\d+$/.test(customRelay)) {
      // It's a pure port number
      wsUrl = `ws://localhost:${customRelay}/ws`;
    } else if (!customRelay.includes('://')) {
      wsUrl = `ws://${customRelay}/ws`;
    } else {
      wsUrl = customRelay;
    }
  }

  // Handle connection errors with a "Hard Reset" as requested
  useEffect(() => {
    if (connectionStatus === 'error') {
      console.warn('Connection failed. Performing hard reset of session cache to defaults...');
      localStorage.removeItem('vision_rcp_session');
      // If it fails after clean URL load, something is fundamentally wrong with the daemon
      if (!window.location.search) {
        useStore.getState().setConnectionStatus('disconnected');
      }
    }
  }, [connectionStatus]);
  
  // FORCE WSS if running on HTTPS (Vercel)
  if (window.location.protocol === 'https:' && wsUrl.startsWith('ws://')) {
    wsUrl = wsUrl.replace('ws://', 'wss://');
  }
  
  const rcp = useRCP(wsUrl, sessionId, relayToken);
  const { login, send } = rcp;
  const [authError, setAuthError] = useState('');
  const [isAuthenticating, setIsAuthenticating] = useState(false);

  // Auto-authentication handshake
  useEffect(() => {
    if (secretKey && !auth.isAuthenticated && connectionStatus === 'connected' && !isAuthenticating && !authError) {
      setIsAuthenticating(true);
      handleLogin(secretKey).catch(() => {
        setIsAuthenticating(false);
      });
    }
  }, [secretKey, auth.isAuthenticated, connectionStatus, isAuthenticating, authError]);

  const handleLogin = async (secret: string) => {
    setAuthError('');
    const cleanSecret = secret.trim().replace(/\|$/, ''); // Clean pipes/spaces
    try {
      await login(cleanSecret);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Login failed';
      setAuthError(msg);
      // If unauthorized, clear stale storage so user isn't stuck
      if (msg.toLowerCase().includes('authorized') || msg.toLowerCase().includes('not found')) {
        localStorage.removeItem('vision_rcp_session');
      }
      throw err;
    }
  };

  /* Unused process command handlers removed for cleanup */
  void send;

  if (!auth.isAuthenticated) {
    return (
      <AuthGate 
        onLogin={handleLogin} 
        error={authError} 
        mode={sessionId ? 'remote' : 'local'}
        sessionId={sessionId}
        isAuthenticating={isAuthenticating}
      />
    );
  }

  return (
    <>
      <Toaster />
      <Layout
        sidebar={<Sidebar rcp={rcp} />}
        main={
          activeTab === 'audit' ? <FlowAudit /> :
          activeTab === 'terminal' ? <ProcessTerminal rcp={rcp} /> :
          <AgentChat rcp={rcp} />
        }
        statusBar={<StatusBar />}
      />
    </>
  );
}

export default App;
