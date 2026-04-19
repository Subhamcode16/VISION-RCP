/**
 * Vision-RCP WebSocket Hook — Connection manager + protocol handler.
 */

import { useCallback, useEffect, useRef } from 'react';
import { createCommand, type CommandType, type Envelope, type LogLine, type ProcessInfo } from '../lib/protocol';
import { useStore } from '../lib/store';
import { useToastStore } from '../lib/toastStore';

/* HEARTBEAT_TIMEOUT removed / unused */
const RECONNECT_BASE = 1000;
const RECONNECT_MAX = 30_000;
const COMMAND_TIMEOUT = 30_000;

export function useRCP(url: string, sessionId?: string, relayToken?: string) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempt = useRef(0);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const pendingRequests = useRef<Map<string, {
    resolve: (v: Envelope) => void;
    reject: (e: Error) => void;
    timer: ReturnType<typeof setTimeout>;
    command: CommandType;
    payload: Record<string, unknown>;
  }>>(new Map());
  const pingTimer = useRef<ReturnType<typeof setInterval> | undefined>(undefined);
  const isRefreshing = useRef(false);

  const {
    setConnectionStatus,
    setLatency,
    auth,
    setAuth,
    clearAuth,
    setProcesses,
    updateProcess,
    appendLog,
    setSystemInfo,
    setGraphs,
    appendAgentMessage,
    setAgentStatus,
    setActiveAdapter,
    appendPacket,
  } = useStore();

  // --- Core API Helpers ---

  const send = useCallback(
    async (command: CommandType, payload: Record<string, unknown> = {}): Promise<Envelope> => {
      return new Promise((resolve, reject) => {
        const ws = wsRef.current;
        if (!ws || ws.readyState !== WebSocket.OPEN) {
          reject(new Error('Not connected'));
          return;
        }

        const envelope = createCommand(command, payload, auth.accessToken ?? undefined);
        const timer = setTimeout(() => {
          pendingRequests.current.delete(envelope.id);
          reject(new Error(`Request timeout: ${command}`));
        }, COMMAND_TIMEOUT);

        pendingRequests.current.set(envelope.id, { 
          resolve, 
          reject, 
          timer,
          command,
          payload
        });
        ws.send(JSON.stringify(envelope));
        appendPacket({ type: 'out', cmd: command, payload });
      });
    },
    [auth.accessToken]
  );

  const refreshSessionInfo = useCallback(async () => {
    const response = await send('session.info');
    if (response.payload) {
      useStore.getState().setSession(response.payload as unknown as import('../lib/protocol').SessionInfo);
    }
  }, [send]);

  const logout = useCallback(async () => {
    try {
      await send('auth.logout', { token: auth.accessToken });
    } catch {
      // Ignore errors on logout
    }
    clearAuth();
  }, [send, auth.accessToken, clearAuth]);

  const handleMessage = (envelope: Envelope) => {
    // Response to a pending request
    if (envelope.ref && pendingRequests.current.has(envelope.ref)) {
      const pending = pendingRequests.current.get(envelope.ref)!;
      clearTimeout(pending.timer);
      pendingRequests.current.delete(envelope.ref);

      if (envelope.type === 'error') {
        // Handle token expiry by attempting a refresh and retry
        if (envelope.error?.code === 'AUTH_INVALID' && auth.refreshToken) {
          // If we hit an auth error, try to refresh instead of instant logout
          console.warn('Auth invalid, attempting silent refresh...');
          refreshTokens()
            .then(() => {
              // Retry the original command with the new token
              const original = pending.command;
              const payload = pending.payload;
              send(original, payload)
                .then(pending.resolve)
                .catch(pending.reject);
            })
            .catch(() => {
              logout();
              pending.reject(new Error('Session expired'));
            });
          return;
        }
        pending.reject(new Error(envelope.error?.message ?? 'Unknown error'));
      } else {
        pending.resolve(envelope);
      }
      return;
    }

    // Heartbeat
    if (envelope.type === 'heartbeat') return;

    // Stream messages
    if (envelope.type === 'stream' && envelope.payload) {
      const payload = envelope.payload;

      if (payload.event === 'state_change' && payload.process) {
        updateProcess(payload.process as ProcessInfo);
      } else if (payload.event === 'relay_status') {
        // Relay status notification
      } else if (payload.stream === 'agent_message' || payload.stream === 'approval_request') {
        const content = String(payload.data);
        
        // Intercept watchdog and error messages for toast feedback
        if (content.startsWith('[WATCHDOG]')) {
          useToastStore.getState().addToast(content.replace('[WATCHDOG]', '').trim(), 'info');
        } else if (content.startsWith('[ERROR]')) {
          useToastStore.getState().addToast(content.replace('[ERROR]', '').trim(), 'error');
        } else if (content.includes('Link established')) {
          useToastStore.getState().addToast('Agent connection established.', 'success');
        }

        appendAgentMessage({
          type: payload.stream === 'agent_message' ? 'AGENT_MESSAGE' : 'APPROVAL_REQUEST',
          content,
          timestamp: Number(payload.ts) * 1000
        });
        if (payload.stream === 'approval_request') {
          setAgentStatus('awaiting_approval');
        }
      } else if (payload.pid && payload.data) {
        appendLog(payload as unknown as LogLine);
      }
    }

    // Ping response → calculate latency
    if (envelope.type === 'response' && envelope.payload?.pong) {
      const serverTs = envelope.payload.ts as number;
      const latency = Math.round(Date.now() - serverTs * 1000);
      setLatency(Math.abs(latency));
    }

    // Always log to audit
    appendPacket({ 
      type: 'in', 
      cmd: envelope.command || (envelope.type as string), 
      payload: envelope.payload || envelope.error || {} 
    });
  };

  const cleanup = () => {
    if (pingTimer.current) clearInterval(pingTimer.current);
    pendingRequests.current.forEach(({ reject, timer }) => {
      clearTimeout(timer);
      reject(new Error('Connection lost'));
    });
    pendingRequests.current.clear();
  };

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    setConnectionStatus('connecting');
    
    let connectionUrl = url;
    if (sessionId && relayToken) {
      const glue = url.includes('?') ? '&' : '?';
      connectionUrl = `${url}${glue}session_id=${sessionId}&token=${relayToken}`;
    }

    const ws = new WebSocket(connectionUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnectionStatus('connected');
      reconnectAttempt.current = 0;

      // Start ping interval
      pingTimer.current = setInterval(() => {
        send('system.ping').catch(() => {});
      }, 10_000);

      // Initial state sync (exempt from auth)
      refreshSessionInfo().catch(() => {});
    };

    ws.onmessage = (event) => {
      try {
        const envelope: Envelope = JSON.parse(event.data);
        handleMessage(envelope);
      } catch {
        // Ignore malformed messages
      }
    };

    ws.onclose = () => {
      setConnectionStatus('disconnected');
      cleanup();
      scheduleReconnect();
    };

    ws.onerror = () => {
      setConnectionStatus('error');
    };
  }, [url, send, refreshSessionInfo]);

  const scheduleReconnect = () => {
    const delay = Math.min(
      RECONNECT_BASE * Math.pow(2, reconnectAttempt.current),
      RECONNECT_MAX,
    );
    reconnectAttempt.current++;
    reconnectTimer.current = setTimeout(connect, delay);
  };


  // Public API
  const login = useCallback(
    async (secret: string) => {
      const response = await send('auth.login', { secret });
      if (response.payload) {
        setAuth(response.payload as { access_token: string; refresh_token: string; expires_at: string });
      }
      return response;
    },
    [send, setAuth],
  );

  const refreshTokens = useCallback(async () => {
    if (isRefreshing.current || !auth.refreshToken) return;
    isRefreshing.current = true;
    
    try {
      const response = await send('auth.refresh', { refresh_token: auth.refreshToken });
      if (response.payload) {
        setAuth(response.payload as { access_token: string; refresh_token: string; expires_at: string });
      } else {
        throw new Error('Refresh failed');
      }
    } catch (e) {
      console.warn('Auth refresh failed:', e);
      logout();
      throw e;
    } finally {
      isRefreshing.current = false;
    }
  }, [send, auth.refreshToken, setAuth, logout]);


  const refreshProcessList = useCallback(async () => {
    const response = await send('process.list');
    if (response.payload?.processes) {
      setProcesses(response.payload.processes as ProcessInfo[]);
    }
  }, [send, setProcesses]);

  const refreshSystemInfo = useCallback(async () => {
    const response = await send('system.info');
    if (response.payload) {
      setSystemInfo(response.payload as unknown as import('../lib/protocol').SystemInfo);
    }
  }, [send, setSystemInfo]);

  const refreshGraphStatus = useCallback(async () => {
    const response = await send('graph.status');
    if (response.payload?.graphs) {
      setGraphs(response.payload.graphs as Record<string, import('../lib/protocol').GraphStatus>);
    }
  }, [send, setGraphs]);


  // Agent API
  const startAgent = useCallback(async (name: string, config: Record<string, unknown> = {}) => {
    const response = await send('agent.start', { name, config });
    if (response.type !== 'error') {
      setActiveAdapter(name);
      setAgentStatus('running');
    }
    return response;
  }, [send, setActiveAdapter, setAgentStatus]);

  const sendAgentMessage = useCallback(async (name: string, message: string) => {
    return await send('agent.send', { name, message });
  }, [send]);

  const stopAgent = useCallback(async (name: string) => {
    const response = await send('agent.stop', { name });
    if (response.type !== 'error') {
      setActiveAdapter(null);
      setAgentStatus('idle');
    }
    return response;
  }, [send, setActiveAdapter, setAgentStatus]);

  const sendApproval = useCallback(async (name: string, decision: boolean) => {
    const response = await send('agent.approve', { name, decision });
    if (response.type !== 'error') {
      setAgentStatus('running');
    }
    return response;
  }, [send, setAgentStatus]);

  // Connect on mount
  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      cleanup();
      wsRef.current?.close();
    };
  }, [connect]);

  // Auto-refresh when authenticated
  useEffect(() => {
    if (!auth.isAuthenticated) return;

    // Helper to safely run background sync tasks
    const sync = () => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
      refreshProcessList().catch(() => {});
      refreshSystemInfo().catch(() => {});
      refreshGraphStatus().catch(() => {});
      refreshSessionInfo().catch(() => {});
    };

    // Initial sync
    sync();

    const interval = setInterval(() => {
      // Silent background refresh check
      if (useStore.getState().isTokenExpiring()) {
        refreshTokens().catch(() => {});
      }

      sync();
    }, 5000);

    return () => clearInterval(interval);
  }, [auth.isAuthenticated]);

  return {
    send,
    login,
    logout,
    refreshProcessList,
    refreshSystemInfo,
    refreshGraphStatus,
    refreshSessionInfo,
    startAgent,
    sendAgentMessage,
    stopAgent,
    sendApproval,
  };
}
