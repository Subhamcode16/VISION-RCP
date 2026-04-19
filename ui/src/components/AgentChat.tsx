import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useStore } from '../lib/store';
import { useRCP } from '../hooks/useRCP';
import { useToastStore } from '../lib/toastStore';
import './AgentChat.css';

interface AgentChatProps {
  rcp: ReturnType<typeof useRCP>;
}

export function AgentChat({ rcp }: AgentChatProps) {
  const { agent, clearAgentMessages } = useStore();
  const addToast = useToastStore((s) => s.addToast);
  const [inputValue, setInputValue] = useState('');
  const [isAutoScroll, setIsAutoScroll] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const [isStarting, setIsStarting] = useState(false);

  const scrollToBottom = useCallback(() => {
    if (isAutoScroll) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'auto' });
    }
  }, [isAutoScroll]);

  useEffect(() => {
    scrollToBottom();
  }, [agent.messages, scrollToBottom]);

  const handleScroll = () => {
    const container = messagesContainerRef.current;
    if (!container) return;
    const { scrollTop, scrollHeight, clientHeight } = container;
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 50;
    setIsAutoScroll(isNearBottom);
  };

  const handleSend = async () => {
    const message = inputValue.trim();
    if (!message) return;

    const activeAdapter = agent.activeAdapter;
    if (!activeAdapter || agent.status !== 'running') return;

    setInputValue('');

    // Handle internal UI commands only
    if (message === '/clear') {
       clearAgentMessages();
       return;
    }

    // Forward message to agent
    // No auto-start here; user must connect manually via the header button if idle

    // Echo user input in the terminal log
    useStore.getState().appendAgentMessage({
      type: 'AGENT_MESSAGE',
      content: `> ${message}`,
      timestamp: Date.now()
    });

    if (activeAdapter && agent.status === 'running') {
      try {
        await rcp.sendAgentMessage(activeAdapter, message);
      } catch (err) {
        // Log Error locally
        useStore.getState().appendAgentMessage({
          type: 'AGENT_MESSAGE',
          content: `!!! ERROR: ${err instanceof Error ? err.message : String(err)}`,
          timestamp: Date.now()
        });
      }
    }
  };

  const handleStart = async () => {
    if (agent.activeAdapter && !isStarting) {
      setIsStarting(true);
      addToast(`Connecting to ${agent.activeAdapter}...`, 'info');
      try {
        const response = await rcp.startAgent(agent.activeAdapter);
        if (response.type === 'error') {
          throw new Error(response.error?.message || 'Failed to start agent');
        }
        addToast(`Agent ${agent.activeAdapter} connected successfully.`, 'success');
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        addToast(`Connection failed: ${msg}`, 'error');
        useStore.getState().appendAgentMessage({
          type: 'AGENT_MESSAGE',
          content: `!!! CONNECTION FAILED: ${msg}`,
          timestamp: Date.now()
        });
      } finally {
        setIsStarting(false);
      }
    }
  };

  const getFriendlyName = (name: string | null) => {
    if (name === 'antigravity') return 'Antigravity Chat Agent';
    if (name === 'antigravity-agent') return 'Antigravity Terminal Bridge';
    return name?.toUpperCase() || 'NO AGENT SELECTED';
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleApproval = async (decision: boolean) => {
    if (agent.activeAdapter) {
      await rcp.sendApproval(agent.activeAdapter, decision);
    }
  };

  return (
    <div className="agent-chat">
      <div className="agent-chat__header">
        <div className="agent-chat__title">
          <span>{getFriendlyName(agent.activeAdapter)}</span>
          {agent.activeAdapter && (
            <span className="agent-chat__adapter-badge">{agent.activeAdapter.toUpperCase()}</span>
          )}
        </div>
        <div className="agent-chat__header-actions">
          <div className={`agent-chat__status ${agent.status}`}>
            <span className={`agent-chat__status-dot ${agent.status !== 'idle' ? 'active' : ''}`}></span>
            {agent.status.toUpperCase()}
          </div>
          <button 
            className="agent-chat__header-btn" 
            onClick={() => clearAgentMessages()}
            title="Clear Buffer"
            style={{ background: 'transparent', border: 'none', color: '#444', cursor: 'pointer', fontSize: '10px' }}
          >
            [CLEAR]
          </button>
        </div>
      </div>

      <div 
        className="agent-chat__messages" 
        ref={messagesContainerRef}
        onScroll={handleScroll}
      >
        {agent.activeAdapter && agent.status === 'idle' ? (
          <div className="agent-chat__onboarding">
            <div className="agent-chat__onboarding-icon">
              {agent.activeAdapter.includes('agent') ? '🐚' : '💬'}
            </div>
            <h3>{getFriendlyName(agent.activeAdapter)}</h3>
            <p>Connection is currently inactive. Click below to initialize the link.</p>
            <button 
              className="btn btn--accent" 
              onClick={handleStart}
              disabled={isStarting}
            >
              {isStarting ? (
                <span className="agent-chat__spinner"></span>
              ) : (
                'CONNECT TO AGENT'
              )}
            </button>
          </div>
        ) : agent.messages.length === 0 ? (
          <div className="agent-chat__message agent" style={{ color: '#404040', padding: '20px' }}>
            Vision-RCP v2.0 Ready.
            Waiting for input...
          </div>
        ) : (
          agent.messages.map((msg, idx) => {
            const isUser = msg.content.startsWith('>');
            const content = msg.content;
            
            if (msg.type === 'APPROVAL_REQUEST') {
              return (
                <div key={idx} className="agent-chat__message-wrapper">
                   <div className="agent-chat__message approval">
                     <div className="agent-chat__approval-title">AUTH REQUIRED</div>
                     <div>{content}</div>
                     {agent.status === 'awaiting_approval' && idx === agent.messages.length - 1 && (
                       <div className="agent-chat__approval-actions">
                         <button onClick={() => handleApproval(true)} className="agent-chat__approval-btn agent-chat__approval-btn--approve">
                           [ACCEPT]
                         </button>
                         <button onClick={() => handleApproval(false)} className="agent-chat__approval-btn agent-chat__approval-btn--reject">
                           [REJECT]
                         </button>
                       </div>
                     )}
                   </div>
                </div>
              );
            }

            if (content === '--- ACK ---') return null;

            return (
              <div key={idx} className="agent-chat__message-wrapper">
                <div className={`agent-chat__message ${isUser ? 'user' : 'agent'}`}>
                  {content}
                </div>
              </div>
            );
          })
        )}
        <div ref={messagesEndRef} />
      </div>

      {!isAutoScroll && (
        <button className="agent-chat__scroll-btn" onClick={() => setIsAutoScroll(true)}>
          ↓
        </button>
      )}

      <div className="agent-chat__input-area">
        <div className="agent-chat__input-container">
          <span className="agent-chat__prompt-symbol">&gt;</span>
          <textarea
            id="agent-chat-input"
            ref={inputRef}
            className="agent-chat__textarea"
            placeholder={agent.status === 'awaiting_approval' ? "" : "..."}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={agent.status === 'awaiting_approval'}
          />
        </div>
      </div>
    </div>
  );
}
