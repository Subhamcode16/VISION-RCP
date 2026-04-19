import React from 'react';
import { useStore } from '../lib/store';
import { useRCP } from '../hooks/useRCP';
import './Sidebar.css';

interface SidebarProps {
  rcp: ReturnType<typeof useRCP>;
}

export function Sidebar({ rcp }: SidebarProps) {
  const { session, agent, activeTab, setActiveTab, setActiveAdapter } = useStore();
  const availableAgents = session?.availableAgents || [];

  const getIcon = (name: string) => {
    if (name.includes('pty') || name.includes('agent')) return '🐚';
    return '💬';
  };

  const getName = (name: string) => {
    if (name === 'antigravity') return 'Chat Agent';
    if (name === 'antigravity-agent') return 'Terminal Bridge';
    return name;
  };

  const handleSelect = (name: string) => {
    if (agent.activeAdapter !== name) {
      setActiveAdapter(name);
    }
  };

  return (
    <div className="sidebar">
      <div className="sidebar__section">
        <div className="sidebar__label mono">AGENTS</div>
        <div className="sidebar__list">
          {availableAgents.map((name) => (
            <div
              key={name}
              className={`sidebar__item ${agent.activeAdapter === name && activeTab === 'agent' ? 'active' : ''}`}
              onClick={() => {
                handleSelect(name);
                setActiveTab('agent');
              }}
            >
              <span className="sidebar__item-icon">{getIcon(name)}</span>
              <span className="sidebar__item-name">{getName(name)}</span>
              {agent.activeAdapter === name && agent.status === 'running' && (
                <span className="sidebar__status-indicator active" />
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="sidebar__section">
        <div className="sidebar__label mono">TOOLS</div>
        <div className="sidebar__list">
          <div 
            className={`sidebar__item ${activeTab === 'audit' ? 'active' : ''}`}
            onClick={() => setActiveTab('audit')}
          >
            <span className="sidebar__item-icon">🔍</span>
            <span className="sidebar__item-name">Flow Audit</span>
          </div>
          <div 
            className={`sidebar__item ${activeTab === 'terminal' ? 'active' : ''}`}
            onClick={() => setActiveTab('terminal')}
          >
            <span className="sidebar__item-icon">💻</span>
            <span className="sidebar__item-name">Terminal</span>
          </div>
        </div>
      </div>

      <div className="sidebar__section sidebar__section--spacer" />

      <div className="sidebar__section">
        <div className="sidebar__label mono">CONNECTION</div>
        <div className="sidebar__connection-details">
          <div className="sidebar__detail">
            <span className="sidebar__detail-label">Port:</span>
            <span className="sidebar__detail-value mono">9077</span>
          </div>
          <div className="sidebar__detail">
            <span className="sidebar__detail-label">Status:</span>
            <span className={`sidebar__detail-value mono ${useStore.getState().connectionStatus}`}>
              {useStore.getState().connectionStatus.toUpperCase()}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
