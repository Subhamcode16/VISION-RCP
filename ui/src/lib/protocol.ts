/**
 * Vision-RCP Protocol — TypeScript type definitions.
 * Mirrors daemon/src/protocol.py exactly.
 */

export type MessageType = 'command' | 'response' | 'stream' | 'error' | 'heartbeat';

export type CommandType =
  | 'process.spawn'
  | 'process.kill'
  | 'process.restart'
  | 'process.list'
  | 'process.status'
  | 'process.logs'
  | 'graph.start'
  | 'graph.stop'
  | 'graph.status'
  | 'auth.login'
  | 'auth.refresh'
  | 'auth.logout'
  | 'system.info'
  | 'system.ping'
  | 'audit.query'
  | 'agent.start'
  | 'agent.send'
  | 'agent.interrupt'
  | 'agent.stop'
  | 'agent.approve'
  | 'session.info';

export type ProcessState =
  | 'pending'
  | 'starting'
  | 'running'
  | 'stopping'
  | 'stopped'
  | 'failed'
  | 'restarting';

export type StreamType = 'stdout' | 'stderr' | 'system';

export interface RCPError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface Envelope {
  id: string;
  type: MessageType;
  ts: string;
  token?: string;
  command?: CommandType;
  ref?: string;
  payload?: Record<string, unknown>;
  error?: RCPError;
}

export interface ProcessInfo {
  name: string;
  cmd: string;
  args: string[];
  cwd?: string;
  depends_on: string[];
  auto_restart: boolean;
  group?: string;
  pid?: number;
  state: ProcessState;
  started_at?: number;
  restart_count: number;
  exit_code?: number;
  uptime: number;
  cpu_percent: number;
  memory_rss: number;
  memory_vms: number;
}

export interface SystemInfo {
  os: string;
  platform: string;
  hostname: string;
  cpu_count: number;
  cpu_percent: number;
  memory_total: number;
  memory_used: number;
  memory_percent: number;
  disk_total: number;
  disk_used: number;
  disk_percent: number;
  uptime: number;
  daemon_port: number;
}

export interface LogLine {
  pid: number;
  name: string;
  stream: StreamType;
  data: string;
  ts: number;
}

export interface GraphNode {
  id: string;
  state: ProcessState;
  pid?: number;
}

export interface GraphEdge {
  from: string;
  to: string;
}

export interface GraphStatus {
  name: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface AgentEvent {
  type: 'AGENT_MESSAGE' | 'APPROVAL_REQUEST' | 'AGENT_STATUS';
  content: string;
  timestamp: number;
  source?: 'user' | 'agent' | 'system';
}

export interface SessionInfo {
  sessionId: string;
  deviceName: string;
  workspace: string;
  agentName: string | null;
  agentStatus: string;
  availableAgents: string[];
  mode: 'local' | 'relay';
  connectedAt: string;
}

/**
 * Create a command envelope.
 */
export function createCommand(
  command: CommandType,
  payload: Record<string, unknown> = {},
  token?: string,
): Envelope {
  return {
    id: crypto.randomUUID(),
    type: 'command',
    ts: new Date().toISOString(),
    command,
    payload,
    token,
  };
}
