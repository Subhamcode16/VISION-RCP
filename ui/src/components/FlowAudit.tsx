import { useEffect, useRef } from 'react';
import { useStore } from '../lib/store';
import { Terminal, Shield, Activity, Trash2 } from 'lucide-react';
import './FlowAudit.css';

export function FlowAudit() {
  const { packetLog, clearPacketLog } = useStore();
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [packetLog]);

  return (
    <div className="flow-audit">
      {/* Header */}
      <div className="flow-audit__header">
        <div className="flow-audit__title-group">
          <Terminal size={14} style={{ color: '#10b981' }} />
          <span className="flow-audit__title">RCP Flow Audit Log</span>
          <span className="flow-audit__badge">LIVE</span>
        </div>
        <button 
          onClick={clearPacketLog}
          className="flow-audit__clear-btn"
          title="Clear Log"
        >
          <Trash2 size={14} />
        </button>
      </div>

      {/* Log View */}
      <div 
        ref={scrollRef}
        className="flow-audit__logs custom-scrollbar"
      >
        {packetLog.length === 0 && (
          <div className="flow-audit__empty">
            <Activity size={32} style={{ marginBottom: '8px', opacity: 0.5 }} />
            <p className="flow-audit__empty-text">Waiting for traffic...</p>
          </div>
        )}
        
        {packetLog.map((p, i) => (
          <div 
            key={i} 
            className={`flow-audit__packet packet-${p.type}`}
          >
            <div className="flow-audit__packet-meta">
              <span className="flow-audit__timestamp">
                {new Date(p.ts).toLocaleTimeString('en-US', { hour12: false })}
              </span>
              
              <span className="flow-audit__type">
                {p.type}
              </span>
              
              <span className="flow-audit__cmd">
                {p.cmd}
              </span>
            </div>

            <div className="flow-audit__payload-container">
               <pre className="flow-audit__payload">
                {JSON.stringify(p.payload, null, 2)}
               </pre>
            </div>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="flow-audit__footer">
        <div className="flow-audit__footer-info">
          <div className="flow-audit__footer-item">
            <Shield size={10} style={{ color: '#3b82f6' }} />
            <span>Encrypted Tunnel</span>
          </div>
          <div className="flow-audit__footer-item">
            <div className="flow-audit__status-dot" />
            <span style={{ color: '#94a3b8' }}>Daemon: 9077</span>
          </div>
        </div>
        <div className="flow-audit__retention">
          Retention: {packetLog.length}/1000 packets
        </div>
      </div>
    </div>
  );
}
