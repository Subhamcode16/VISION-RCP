/**
 * Vision-RCP Layout — Main 3-panel grid layout with session-aware header.
 */

import React, { type ReactNode } from 'react';
import { Menu } from 'lucide-react';
import { useStore } from '../lib/store';
import './Layout.css';

interface LayoutProps {
  sidebar: ReactNode;
  main: ReactNode;
  statusBar: ReactNode;
}

export function Layout({ sidebar, main, statusBar }: LayoutProps) {
  const { session, connectionStatus, isSidebarOpen, setIsSidebarOpen } = useStore();

  return (
    <div className={`layout ${connectionStatus} ${isSidebarOpen ? 'sidebar-open' : ''}`}>
      <header className="layout__topbar">
        <div className="layout__brand">
          <button 
            className="layout__menu-toggle"
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            aria-label="Toggle Sidebar"
          >
            <Menu size={20} />
          </button>
          <span className="layout__icon">⬡</span>
          <span className="layout__title mono">VISION-RCP</span>
        </div>
        
        {session && (
          <div className="layout__session-info">
            <div className="layout__session-item">
              <span className="layout__label">DEVICE:</span>
              <span className="layout__value mono">{session.deviceName}</span>
            </div>
            <div className="layout__session-divider"></div>
            <div className="layout__session-item">
              <span className="layout__label">SESSION:</span>
              <span className="layout__value mono">{session.sessionId}</span>
            </div>
            <div className="layout__session-divider hide-mobile"></div>
            <div className="layout__session-item hide-mobile">
              <span className="layout__label">WORKSPACE:</span>
              <span className="layout__value mono">{session.workspace}</span>
            </div>
            <span className={`layout__mode-badge ${session.mode}`}>
              {session.mode.toUpperCase()}
            </span>
          </div>
        )}

        <div className="layout__top-actions">
           {/* Add user profile or logout here if needed */}
        </div>
      </header>

      <div className="layout__body">
        <div 
          className={`layout__overlay ${isSidebarOpen ? 'active' : ''}`}
          onClick={() => setIsSidebarOpen(false)}
        />
        {sidebar && (sidebar as any).type !== React.Fragment && (
          <aside className={`layout__sidebar ${isSidebarOpen ? 'active' : ''}`}>{sidebar}</aside>
        )}
        <main className="layout__main">{main}</main>
      </div>

      {statusBar}
    </div>
  );
}

