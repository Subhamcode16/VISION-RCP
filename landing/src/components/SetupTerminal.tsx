import React, { useState, useEffect } from 'react';

const steps = [
  {
    id: 'clone',
    label: '1. Clone',
    content: [
      { type: 'comment', text: '# Fetch the control plane' },
      { type: 'command', text: 'git clone https://github.com/vision-rcp/vision-rcp.git' },
      { type: 'command', text: 'cd vision-rcp' }
    ]
  },
  {
    id: 'launch',
    label: '2. Launch',
    content: [
      { type: 'comment', text: '# Start daemon and dashboard' },
      { type: 'command', text: './start-app.bat' },
      { type: 'output', text: '> Installing dependencies...' },
      { type: 'output', text: '> Vision-RCP Daemon online [Port 9077]' }
    ]
  },
  {
    id: 'connect',
    label: '3. Connect',
    content: [
      { type: 'comment', text: '# Access via mobile or desktop' },
      { type: 'output', text: '> Remote Tunnel: https://vision-rcp.dev/a7b2' },
      { type: 'output', text: '> Local UI: http://localhost:5173' }
    ]
  }
];

export const SetupTerminal: React.FC = () => {
  const [activeTab, setActiveTab] = useState('clone');
  const [visibleLinesCount, setVisibleLinesCount] = useState(0);
  const [typingIndex, setTypingIndex] = useState(0);

  const activeContent = steps.find(s => s.id === activeTab)?.content || [];

  useEffect(() => {
    // Reset animation when tab changes
    setVisibleLinesCount(0);
    setTypingIndex(0);
  }, [activeTab]);

  useEffect(() => {
    if (visibleLinesCount >= activeContent.length) return;

    const currentLine = activeContent[visibleLinesCount];
    
    if (currentLine.type === 'command') {
      if (typingIndex < currentLine.text.length) {
        // Typing commands character by character
        const timeout = setTimeout(() => {
          setTypingIndex(prev => prev + 1);
        }, 20 + Math.random() * 20); // Variable speed for realism
        return () => clearTimeout(timeout);
      } else {
        // Command finished, move to next line after pause
        const timeout = setTimeout(() => {
          setVisibleLinesCount(prev => prev + 1);
          setTypingIndex(0);
        }, 300);
        return () => clearTimeout(timeout);
      }
    } else {
      // Comments and outputs appear instantly
      const timeout = setTimeout(() => {
        setVisibleLinesCount(prev => prev + 1);
        setTypingIndex(0);
      }, 150);
      return () => clearTimeout(timeout);
    }
  }, [visibleLinesCount, typingIndex, activeContent, activeTab]);

  return (
    <div className="setup-terminal">
      <div className="terminal-tabs">
        {steps.map(s => (
          <button
            key={s.id}
            className={`terminal-tab ${activeTab === s.id ? 'active' : ''}`}
            onClick={() => setActiveTab(s.id)}
          >
            {s.label}
          </button>
        ))}
      </div>
      <div className="terminal-window">
        <div className="terminal-header">
          <div className="dots">
            <div className="dot red"></div>
            <div className="dot yellow"></div>
            <div className="dot green"></div>
          </div>
          <div className="terminal-title">powershell</div>
        </div>
        <div className="terminal-body px-6 py-8">
          {activeContent.slice(0, visibleLinesCount + 1).map((line, i) => {
            const isLastVisible = i === visibleLinesCount;
            if (!isLastVisible) {
                // Completed lines
                return (
                    <div key={i} className={`terminal-line ${line.type} opacity-100`}>
                        {line.type === 'command' && <span className="prompt">$ </span>}
                        {line.text}
                    </div>
                );
            }

            // Line currently being typed/revealed
            const displayText = line.type === 'command' 
                ? line.text.substring(0, typingIndex) 
                : line.text;

            return (
              <div key={i} className={`terminal-line ${line.type} animate-in`}>
                {line.type === 'command' && <span className="prompt">$ </span>}
                {displayText}
                {isLastVisible && i < activeContent.length && (
                    <span className="terminal-cursor">_</span>
                )}
              </div>
            );
          })}
        </div>
      </div>
      <style>{`
        .setup-terminal {
          margin-top: 4rem;
          max-width: 800px;
          margin-left: auto;
          margin-right: auto;
        }
        .terminal-tabs {
          display: flex;
          gap: 0.5rem;
          margin-bottom: 0.5rem;
        }
        .terminal-tab {
          background: #18181b;
          border: 1px solid #27272a;
          color: #71717a;
          padding: 0.5rem 1rem;
          border-radius: 8px 8px 0 0;
          font-size: 0.875rem;
          cursor: pointer;
          transition: all 0.2s;
        }
        .terminal-tab.active {
          background: #27272a;
          color: white;
          border-bottom-color: #3b82f6;
        }
        .terminal-window {
          background: #000;
          border: 1px solid #27272a;
          border-radius: 0 12px 12px 12px;
          overflow: hidden;
          box-shadow: 0 40px 80px -20px rgba(0, 0, 0, 0.8);
        }
        .terminal-header {
          background: #18181b;
          padding: 0.75rem 1rem;
          display: flex;
          align-items: center;
          border-bottom: 1px solid #27272a;
        }
        .dots { display: flex; gap: 0.4rem; }
        .dot { width: 10px; height: 10px; border-radius: 50%; opacity: 0.6; }
        .red { background: #ff5f56; }
        .yellow { background: #ffbd2e; }
        .green { background: #27c93f; }
        .terminal-title { margin-left: 1rem; font-size: 0.75rem; color: #52525b; font-family: monospace; }
        .terminal-body {
          padding: 1.5rem;
          font-family: 'JetBrains Mono', monospace;
          min-height: 240px;
        }
        .terminal-line { 
            margin-bottom: 0.6rem; 
            font-size: 0.9375rem; 
            opacity: 1; 
            transition: opacity 0.3s;
        }
        .terminal-line.animate-in {
            animation: fadeIn 0.2s ease-out;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(4px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .terminal-line.comment { color: #52525b; }
        .terminal-line.command { color: #f4f4f5; }
        .terminal-line.output { color: #27c93f; }
        .prompt { color: #3b82f6; font-weight: 700; margin-right: 0.5rem; }
        
        .terminal-cursor {
            display: inline-block;
            width: 8px;
            height: 1.2em;
            background: #fff;
            margin-left: 4px;
            vertical-align: middle;
            animation: blink 0.8s step-end infinite;
        }
        @keyframes blink {
            50% { opacity: 0; }
        }
      `}</style>
    </div>
  );
};
