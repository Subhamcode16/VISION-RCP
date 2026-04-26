import React from 'react';
import { SectionWrapper } from './ui/SectionWrapper';

export const WhatItDoes: React.FC = () => {
  return (
    <SectionWrapper id="features" className="what-it-does-section">
      <div className="section-header text-center mb-16">
        <h1 className="section-header-h1">The Brain of your Agent Fleet</h1>
        <p className="section-subtitle text-neutral text-lg md:text-xl max-w-2xl mx-auto">Vision-RCP doesn't just monitor; it orchestrates the entire specialized Antigravity ecosystem.</p>
      </div>

      <div className="bento-grid">
        <div className="bento-card large">
          <div className="bento-tag">Core Engine</div>
          <h3>The Antigravity Bridge</h3>
          <p>Seamlessly proxy local OS-level automation commands to a high-performance web interface. No latency, no fragmentation.</p>
          <div className="bento-stat">
            <span className="stat-value">50ms</span>
            <span className="stat-label">End-to-end Latency</span>
          </div>
        </div>

        <div className="bento-card">
          <div className="bento-icon">🕵️</div>
          <h4>Deep Audit</h4>
          <p>Inspect every packet sent between the daemon and agents. Perfect for security grounding.</p>
        </div>

        <div className="bento-card">
          <div className="bento-icon">🔄</div>
          <h4>Session Recovery</h4>
          <p>Crashed processes? Vision-RCP auto-heals and restores session state automatically.</p>
        </div>

        <div className="bento-card wide">
          <div className="bento-icon">📲</div>
          <div className="wide-content">
            <h4>Remote Desktop Automation</h4>
            <p>Control the Antigravity desktop agent from any mobile browser with full RPA capabilities across the WAN.</p>
          </div>
        </div>
      </div>

      <style>{`
        .bento-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          grid-template-rows: auto auto;
          gap: 1.5rem;
          margin-top: 4rem;
        }
        .bento-card {
          background: rgba(18, 18, 20, 0.4);
          backdrop-filter: blur(12px);
          border: 1px solid rgba(255, 255, 255, 0.05);
          padding: 2.5rem;
          border-radius: 24px;
          display: flex;
          flex-direction: column;
          gap: 1rem;
          transition: all 0.3s ease;
        }
        .bento-card:hover {
          border-color: rgba(255, 255, 255, 0.3);
          background: rgba(18, 18, 20, 0.6);
          transform: translateY(-4px);
          box-shadow: 0 20px 40px -20px rgba(0, 0, 0, 0.5);
        }
        .bento-card.large {
          grid-row: span 2;
          background: linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(9, 9, 11, 0) 100%), rgba(18, 18, 20, 0.4);
        }
        .bento-card.wide {
          grid-column: span 2;
          flex-direction: row;
          align-items: center;
        }
        .bento-tag {
          font-size: 10px;
          text-transform: uppercase;
          letter-spacing: 0.1em;
          color: #ffffff;
          font-weight: 700;
        }
        .bento-card h3 { font-size: 2rem; margin-bottom: 0.5rem; }
        .bento-card h4 { font-size: 1.25rem; font-weight: 600; }
        .bento-card p { color: #a1a1aa; line-height: 1.5; }
        .bento-stat { margin-top: auto; display: flex; flex-direction: column; }
        .stat-value { font-size: 3rem; font-weight: 800; color: white; }
        .stat-label { font-size: 0.875rem; color: #71717a; }
        .bento-icon { font-size: 2.5rem; }

        @media (max-width: 900px) {
          .bento-grid { grid-template-columns: 1fr; }
          .bento-card.large, .bento-card.wide { grid-row: auto; grid-column: auto; }
        }
      `}</style>
    </SectionWrapper>
  );
};
