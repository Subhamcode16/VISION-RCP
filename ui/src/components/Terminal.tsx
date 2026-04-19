import { useEffect, useRef } from 'react';
import { useRCP } from '../hooks/useRCP';
import { Terminal as XTerm } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import { SearchAddon } from '@xterm/addon-search';
import { WebLinksAddon } from '@xterm/addon-web-links';
import { useStore } from '../lib/store';
import '@xterm/xterm/css/xterm.css';
import './Terminal.css';

const THEME = {
  background: '#0C0C0E',
  foreground: '#E8E8EA',
  cursor: '#3B82F6',
  cursorAccent: '#0C0C0E',
  selectionBackground: 'rgba(59, 130, 246, 0.3)',
  selectionForeground: '#E8E8EA',
  black: '#0C0C0E',
  red: '#EF4444',
  green: '#22C55E',
  yellow: '#F59E0B',
  blue: '#3B82F6',
  magenta: '#A855F7',
  cyan: '#06B6D4',
  white: '#E8E8EA',
  brightBlack: '#4A4A50',
  brightRed: '#F87171',
  brightGreen: '#4ADE80',
  brightYellow: '#FBBF24',
  brightBlue: '#60A5FA',
  brightMagenta: '#C084FC',
  brightCyan: '#22D3EE',
  brightWhite: '#FFFFFF',
};

interface TerminalProps {
  rcp: ReturnType<typeof useRCP>;
}

export function Terminal({ rcp }: TerminalProps) {
  void rcp;
  const termRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<XTerm | null>(null);
  const fitRef = useRef<FitAddon | null>(null);
  const { selectedPid, logs } = useStore();

  // Initialize terminal
  useEffect(() => {
    if (!termRef.current) return;

    const term = new XTerm({
      theme: THEME,
      fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
      fontSize: 13,
      lineHeight: 1.4,
      letterSpacing: 0,
      cursorBlink: true,
      cursorStyle: 'bar',
      scrollback: 10000,
      convertEol: true,
      allowProposedApi: true,
    });

    const fitAddon = new FitAddon();
    const searchAddon = new SearchAddon();
    const webLinksAddon = new WebLinksAddon();

    term.loadAddon(fitAddon);
    term.loadAddon(searchAddon);
    term.loadAddon(webLinksAddon);

    term.open(termRef.current);
    fitAddon.fit();

    xtermRef.current = term;
    fitRef.current = fitAddon;

    // Handle resize
    const resizeObserver = new ResizeObserver(() => {
      try {
        fitAddon.fit();
      } catch {
        // Ignore fit errors during transitions
      }
    });
    resizeObserver.observe(termRef.current);

    return () => {
      resizeObserver.disconnect();
      term.dispose();
    };
  }, []);

  // Write logs to terminal
  useEffect(() => {
    const term = xtermRef.current;
    if (!term) return;

    term.clear();

    if (selectedPid === null) {
      // Show all process output with process name prefixed
      term.writeln('\x1b[2m── All process output ──\x1b[0m');
      term.writeln('');

      // Merge and sort all logs
      const allLogs = Object.values(logs).flat().sort((a, b) => a.ts - b.ts);
      for (const line of allLogs.slice(-500)) {
        writeLogLine(term, line.name, line.stream, line.data);
      }
    } else {
      // Show selected process output
      const processLogs = logs[selectedPid] || [];
      for (const line of processLogs) {
        writeLogLine(term, line.name, line.stream, line.data);
      }
    }

    term.scrollToBottom();
  }, [selectedPid, logs]);

  return (
    <div className="terminal-container">
      <div className="terminal-header">
        <span className="terminal-header__title mono text-xs">
          {selectedPid !== null ? `PID ${selectedPid}` : 'ALL STREAMS'}
        </span>
        <button
          className="btn btn--sm"
          onClick={() => xtermRef.current?.clear()}
        >
          Clear
        </button>
      </div>
      <div className="terminal-body" ref={termRef} />
    </div>
  );
}

function writeLogLine(term: XTerm, name: string, stream: string, data: string) {
  const prefix = `\x1b[2m[${name}]\x1b[0m `;
  if (stream === 'stderr') {
    term.writeln(`${prefix}\x1b[31m${data}\x1b[0m`);
  } else if (stream === 'system') {
    term.writeln(`${prefix}\x1b[33m${data}\x1b[0m`);
  } else {
    term.writeln(`${prefix}${data}`);
  }
}
