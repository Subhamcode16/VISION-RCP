/**
 * Vision-RCP Layout — Main 3-panel grid layout with session-aware header.
 */

import React, { type ReactNode } from 'react';
import { useStore } from '../lib/store';
import './Layout.css';

interface LayoutProps {
  sidebar: ReactNode;
  main: ReactNode;
  statusBar: ReactNode;
}

export function Layout({ sidebar, main, statusBar }: LayoutProps) {
  const { session, connectionStatus } = useStore();

  return (
    <div className={`layout ${connectionStatus}`}>
      <header className="layout__topbar">
        <div className="layout__brand">
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
        {sidebar && (sidebar as any).type !== React.Fragment && (
          <aside className="layout__sidebar">{sidebar}</aside>
        )}
        <main className="layout__main">{main}</main>
      </div>

      {statusBar}
    </div>
  );
}

