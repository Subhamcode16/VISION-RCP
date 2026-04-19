import { useStore } from '../lib/store';
import { useRCP } from '../hooks/useRCP';
import { 
  Bot, 
  Terminal, 
  Activity, 
  Cpu,
  Wifi,
  WifiOff,
  X
} from 'lucide-react';
import './Sidebar.css';

interface SidebarProps {
  rcp: ReturnType<typeof useRCP>;
}

export function Sidebar({ rcp }: SidebarProps) {
  void rcp;
  const { 
    session, 
    agent, 
    activeTab, 
    setActiveTab, 
    setActiveAdapter, 
    connectionStatus,
    setIsSidebarOpen 
  } = useStore();
  const availableAgents = session?.availableAgents || [];

  const getIcon = (name: string) => {
    if (name.includes('pty') || name.includes('agent')) return <Terminal size={18} />;
    return <Bot size={18} />;
  };

  const getName = (name: string) => {
    if (name === 'antigravity') return 'Vision Agent';
    if (name === 'antigravity-agent') return 'Terminal Link';
    return name.charAt(0).toUpperCase() + name.slice(1);
  };

  const handleSelect = (name: string) => {
    if (agent.activeAdapter !== name) {
      setActiveAdapter(name);
    }
  };

  return (
    <div className="sidebar animate-fade-in">
      <div className="sidebar__mobile-header">
        <span className="sidebar__mobile-title mono">MENU</span>
        <button 
          className="sidebar__close-btn"
          onClick={() => setIsSidebarOpen(false)}
        >
          <X size={20} />
        </button>
      </div>
      {/* Agents Section */}
      <div className="sidebar__section">
        <div className="sidebar__label">Agents</div>
        <div className="sidebar__list">
          {availableAgents.map((name) => (
            <div
              key={name}
              className={`sidebar__item ${agent.activeAdapter === name && activeTab === 'agent' ? 'active' : ''}`}
              onClick={() => {
                handleSelect(name);
                setActiveTab('agent');
                setIsSidebarOpen(false);
              }}
            >
              <span className="sidebar__item-icon">{getIcon(name)}</span>
              <span className="sidebar__item-name">{getName(name)}</span>
              <span className={`sidebar__status-indicator ${agent.activeAdapter === name && agent.status === 'running' ? 'active' : ''}`} />
            </div>
          ))}
          {availableAgents.length === 0 && (
            <div className="text-[11px] text-zinc-600 px-3 py-2 italic">No agents found</div>
          )}
        </div>
      </div>

      {/* Tools Section */}
      <div className="sidebar__section">
        <div className="sidebar__label">System Tools</div>
        <div className="sidebar__list">
          <div 
            className={`sidebar__item ${activeTab === 'audit' ? 'active' : ''}`}
            onClick={() => {
              setActiveTab('audit');
              setIsSidebarOpen(false);
            }}
          >
            <span className="sidebar__item-icon"><Activity size={18} /></span>
            <span className="sidebar__item-name">Flow Audit</span>
          </div>
          <div 
            className={`sidebar__item ${activeTab === 'terminal' ? 'active' : ''}`}
            onClick={() => {
              setActiveTab('terminal');
              setIsSidebarOpen(false);
            }}
          >
            <span className="sidebar__item-icon"><Terminal size={18} /></span>
            <span className="sidebar__item-name">Root Terminal</span>
          </div>
        </div>
      </div>

      <div className="sidebar__section sidebar__section--spacer" />

      {/* Connection Info */}
      <div className="sidebar__section">
        <div className="sidebar__label">Infrastructure</div>
        <div className="sidebar__connection-details">
          <div className="sidebar__detail">
            <span className="sidebar__detail-label">Port</span>
            <span className="sidebar__detail-value">9077</span>
          </div>
          <div className="sidebar__detail">
            <span className="sidebar__detail-label">Engine</span>
            <div className="flex items-center gap-1.5 sidebar__detail-value">
              <Cpu size={10} className="text-zinc-500" />
              <span>RCP-v2</span>
            </div>
          </div>
          <div className="sidebar__detail">
            <span className="sidebar__detail-label">Status</span>
            <div className={`flex items-center gap-1.5 sidebar__detail-value ${connectionStatus}`}>
              {connectionStatus === 'connected' ? <Wifi size={12} /> : <WifiOff size={12} />}
              <span className="uppercase tracking-wider font-bold text-[9px]">
                {connectionStatus}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
