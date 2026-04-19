/**
 * Vision-RCP StatusBar — Bottom bar showing connection status, system metrics, latency.
 */

import { useStore } from '../lib/store';
import './StatusBar.css';

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0';
  const units = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(0)} ${units[i]}`;
}

export function StatusBar() {
  const { connectionStatus, latency, systemInfo, processes, auth } = useStore();

  const statusClass =
    connectionStatus === 'connected' ? 'live' :
    connectionStatus === 'connecting' ? 'starting' :
    connectionStatus === 'error' ? 'error' : 'idle';

  const runningCount = processes.filter((p) => p.state === 'running').length;

  return (
    <footer className="status-bar">
      <div className="status-bar__left">
        <span className="status-bar__item">
          <span className={`status-dot status-dot--${statusClass}`} />
          <span className="mono text-xs">{connectionStatus.toUpperCase()}</span>
        </span>

        {auth.isAuthenticated && (
          <span className="status-bar__item text-xs text-muted">
            ● AUTHENTICATED
          </span>
        )}
      </div>

      <div className="status-bar__center">
        <span className="status-bar__item text-xs mono">
          {runningCount} running / {processes.length} total
        </span>
      </div>

      <div className="status-bar__right">
        {systemInfo && (
          <>
            <span className="status-bar__item text-xs mono">
              CPU {systemInfo.cpu_percent.toFixed(0)}%
            </span>
            <span className="status-bar__item text-xs mono">
              MEM {formatBytes(systemInfo.memory_used)} / {formatBytes(systemInfo.memory_total)}
              ({systemInfo.memory_percent.toFixed(0)}%)
            </span>
            <span className="status-bar__item text-xs mono">
              {systemInfo.hostname}
            </span>
          </>
        )}
        <span className="status-bar__item text-xs mono text-muted">
          {latency}ms
        </span>
      </div>
    </footer>
  );
}
