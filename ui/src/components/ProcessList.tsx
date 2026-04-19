/**
 * Vision-RCP ProcessList — Live process table with status indicators.
 */

import { useStore } from '../lib/store';
import type { ProcessState, ProcessInfo } from '../lib/protocol';
import './ProcessList.css';

interface ProcessListProps {
  onKill: (pid: number) => void;
  onRestart: (pid: number) => void;
}

function stateToClass(state: ProcessState): string {
  switch (state) {
    case 'running':    return 'live';
    case 'starting':
    case 'restarting': return 'starting';
    case 'failed':     return 'error';
    case 'stopping':
    case 'stopped':    return 'idle';
    default:           return 'idle';
  }
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '—';
  const units = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}

function formatUptime(seconds: number): string {
  if (seconds <= 0) return '—';
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
}

export function ProcessList({ onKill, onRestart }: ProcessListProps) {
  const { processes, selectedPid, selectProcess } = useStore();

  if (processes.length === 0) {
    return (
      <div className="process-list process-list--empty">
        <p className="process-list__empty-text">No managed processes</p>
        <p className="text-xs text-muted">
          Spawn a process using the command bar or start a process group.
        </p>
      </div>
    );
  }

  return (
    <div className="process-list">
      <div className="process-list__header">
        <span>PROCESSES</span>
        <span className="text-xs text-muted">{processes.length}</span>
      </div>

      <div className="process-list__body">
        {processes.map((proc) => (
          <div
            key={proc.name}
            className={`process-row ${proc.pid === selectedPid ? 'process-row--selected' : ''}`}
            onClick={() => selectProcess(proc.pid ?? null)}
          >
            <div className="process-row__main">
              <span className={`status-dot status-dot--${stateToClass(proc.state)}`} />
              <span className="process-row__name mono">{proc.name}</span>
              <span className="process-row__state text-xs text-muted">{proc.state}</span>
            </div>

            <div className="process-row__metrics text-xs mono">
              {proc.pid && <span className="process-row__pid">PID {proc.pid}</span>}
              {proc.cpu_percent > 0 && (
                <span className="process-row__cpu">{proc.cpu_percent.toFixed(1)}%</span>
              )}
              {proc.memory_rss > 0 && (
                <span className="process-row__mem">{formatBytes(proc.memory_rss)}</span>
              )}
              <span className="process-row__uptime">{formatUptime(proc.uptime)}</span>
            </div>

            {proc.state === 'running' && proc.pid && (
              <div className="process-row__actions">
                <button
                  className="btn btn--sm"
                  onClick={(e) => { e.stopPropagation(); onRestart(proc.pid!); }}
                  title="Restart"
                >
                  ↻
                </button>
                <button
                  className="btn btn--sm btn--danger"
                  onClick={(e) => { e.stopPropagation(); onKill(proc.pid!); }}
                  title="Kill"
                >
                  ✕
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
