/**
 * Vision-RCP Store — Zustand global state management.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { ProcessInfo, SystemInfo, LogLine, GraphStatus, AgentEvent, SessionInfo } from './protocol';

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

export interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  expiresAt: string | null;
  isAuthenticated: boolean;
}

interface RCPState {
  /* Connection */
  connectionStatus: ConnectionStatus;
  latency: number;
  setConnectionStatus: (s: ConnectionStatus) => void;
  setLatency: (ms: number) => void;

  /* Auth */
  auth: AuthState;
  setAuth: (tokens: { access_token: string; refresh_token: string; expires_at: string }) => void;
  clearAuth: () => void;

  /* Processes */
  processes: ProcessInfo[];
  selectedPid: number | null;
  setProcesses: (p: ProcessInfo[]) => void;
  updateProcess: (p: ProcessInfo) => void;
  selectProcess: (pid: number | null) => void;

  /* Logs */
  logs: Record<number, LogLine[]>;
  appendLog: (line: LogLine) => void;
  clearLogs: (pid: number) => void;

  /* System */
  systemInfo: SystemInfo | null;
  setSystemInfo: (info: SystemInfo) => void;

  /* Graphs */
  graphs: Record<string, GraphStatus>;
  setGraphs: (g: Record<string, GraphStatus>) => void;

  /* Agent */
  agent: {
    messages: AgentEvent[];
    status: 'idle' | 'running' | 'awaiting_approval';
    activeAdapter: string | null;
  };
  appendAgentMessage: (msg: AgentEvent) => void;
  setAgentStatus: (status: 'idle' | 'running' | 'awaiting_approval') => void;
  setActiveAdapter: (name: string | null) => void;
  clearAgentMessages: () => void;
  processedUids: Set<string>;

  /* Session */
  session: SessionInfo | null;
  setSession: (info: SessionInfo) => void;

  /* UI */
  activeTab: 'terminal' | 'graph' | 'audit' | 'agent';
  isSidebarOpen: boolean;
  setActiveTab: (t: 'terminal' | 'graph' | 'audit' | 'agent') => void;
  setIsSidebarOpen: (open: boolean) => void;

  /* Audit */
  packetLog: { type: 'in' | 'out', cmd: string, payload: any, ts: number }[];
  appendPacket: (p: { type: 'in' | 'out', cmd: string, payload: any }) => void;
  clearPacketLog: () => void;

  /* Helpers */
  isTokenExpiring: () => boolean;
}

const MAX_LOG_LINES = 5000;

export const useStore = create<RCPState>()(
  persist(
    (set, get) => ({
  /* Connection */
  connectionStatus: 'disconnected',
  latency: 0,
  setConnectionStatus: (connectionStatus) => set({ connectionStatus }),
  setLatency: (latency) => set({ latency }),

  /* Auth */
  auth: {
    accessToken: null,
    refreshToken: null,
    expiresAt: null,
    isAuthenticated: false,
  },
  setAuth: (tokens) =>
    set({
      auth: {
        accessToken: tokens.access_token,
        refreshToken: tokens.refresh_token,
        expiresAt: tokens.expires_at,
        isAuthenticated: true,
      },
    }),
  clearAuth: () =>
    set({
      auth: {
        accessToken: null,
        refreshToken: null,
        expiresAt: null,
        isAuthenticated: false,
      },
    }),

  /* Processes */
  processes: [],
  selectedPid: null,
  setProcesses: (processes) => set({ processes }),
  updateProcess: (updated) =>
    set((state) => ({
      processes: state.processes.some((p) => p.name === updated.name)
        ? state.processes.map((p) => (p.name === updated.name ? updated : p))
        : [...state.processes, updated],
    })),
  selectProcess: (selectedPid) => set({ selectedPid }),

  /* Logs */
  logs: {},
  appendLog: (line) =>
    set((state) => {
      const existing = state.logs[line.pid] || [];
      const updated = [...existing, line];
      return {
        logs: {
          ...state.logs,
          [line.pid]: updated.length > MAX_LOG_LINES
            ? updated.slice(-MAX_LOG_LINES)
            : updated,
        },
      };
    }),
  clearLogs: (pid) =>
    set((state) => {
      const logs = { ...state.logs };
      delete logs[pid];
      return { logs };
    }),

  /* System */
  systemInfo: null,
  setSystemInfo: (systemInfo) => set({ systemInfo }),

  /* Graphs */
  graphs: {},
  setGraphs: (graphs) => set({ graphs }),

  /* Agent */
  agent: {
    messages: [],
    status: 'idle',
    activeAdapter: null,
  },
  processedUids: new Set<string>(),
  appendAgentMessage: (msg) =>
    set((state) => {
      // 1. UID Deduplication (Stage UUID)
      if (msg.uid && state.processedUids.has(msg.uid)) {
        console.debug('[STORE] Dropping duplicate message by UID:', msg.uid);
        return state;
      }

      // 2. Content Deduplication (Existing guard)
      const lastMsg = state.agent.messages[state.agent.messages.length - 1];
      if (lastMsg && lastMsg.content === msg.content && lastMsg.type === msg.type) {
        return state;
      }

      // Track UID if provided
      if (msg.uid) {
        state.processedUids.add(msg.uid);
      }

      return {
        agent: { ...state.agent, messages: [...state.agent.messages, msg] },
      };
    }),
  setAgentStatus: (status) =>
    set((state) => ({
      agent: { ...state.agent, status },
    })),
  setActiveAdapter: (name) =>
    set((state) => ({
      agent: { ...state.agent, activeAdapter: name },
    })),
  clearAgentMessages: () =>
    set((state) => ({
      agent: { ...state.agent, messages: [] },
    })),

  /* Session */
  session: null,
  setSession: (raw: any) => set((state) => {
    const sessionInfo: SessionInfo = {
      sessionId: raw.session_id || raw.sessionId || 'LOCAL',
      deviceName: raw.device_name || raw.deviceName || 'Unknown',
      workspace: raw.workspace || '',
      agentName: raw.agent_name || raw.agentName || null,
      agentStatus: raw.agent_status || raw.agentStatus || 'idle',
      availableAgents: raw.available_agents || raw.availableAgents || [],
      mode: raw.mode || 'local',
      connectedAt: raw.connected_at || raw.connectedAt || new Date().toISOString()
    };
    
    return {
      session: sessionInfo,
      agent: {
        ...state.agent,
        // Backend is the source of truth for the active adapter
        activeAdapter: sessionInfo.agentName || state.agent.activeAdapter,
        status: sessionInfo.agentStatus === 'running' 
          ? 'running' 
          : (sessionInfo.agentStatus === 'idle' ? 'idle' : state.agent.status)
      }
    };
  }),

  /* UI */
  activeTab: 'terminal',
  isSidebarOpen: false,
  setActiveTab: (activeTab) => set({ activeTab }),
  setIsSidebarOpen: (isSidebarOpen) => set({ isSidebarOpen }),

  /* Audit */
  packetLog: [],
  appendPacket: (p) => set((state) => ({ 
    packetLog: [...state.packetLog, { ...p, ts: Date.now() }].slice(-1000) 
  })),
  clearPacketLog: () => set({ packetLog: [] }),

  /* Helpers */
  isTokenExpiring: () => {
    const { expiresAt } = get().auth;
    if (!expiresAt) return false;
    const expiry = new Date(expiresAt).getTime();
    const now = Date.now();
    // Return true if expiring within 5 minutes
    return expiry - now < 5 * 60 * 1000;
  },
    }),
    {
      name: 'vision-rcp-storage',
      partialize: (state) => ({ auth: state.auth, activeTab: state.activeTab }),
    }
  )
);
