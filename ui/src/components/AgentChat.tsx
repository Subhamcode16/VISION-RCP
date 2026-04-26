import { useState, useRef, useEffect, useCallback } from 'react';
import { useStore } from '../lib/store';
import { useRCP } from '../hooks/useRCP';
import { useToastStore } from '../lib/toastStore';
import { 
  Bot, 
  Terminal as TerminalIcon, 
  Trash2, 
  ArrowDown, 
  MessagesSquare,
  ShieldAlert,
  Loader2,
  Zap
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './AgentChat.css';
import AiChatInput from './ui/ai-chat-input';
import agentAvatar from '../assets/vision_agent_logo.png';

const UserAvatar = () => (
  <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full opacity-60">
    <path d="M12 12C14.2091 12 16 10.2091 16 8C16 5.79086 14.2091 4 12 4C9.79086 4 8 5.79086 8 8C8 10.2091 9.79086 12 12 12Z" fill="currentColor"/>
    <path d="M12 14C8.68629 14 6 16.6863 6 20H18C18 16.6863 15.3137 14 12 14Z" fill="currentColor"/>
  </svg>
);

interface AgentChatProps {
  rcp: ReturnType<typeof useRCP>;
}

export function AgentChat({ rcp }: AgentChatProps) {
  const { agent, clearAgentMessages, connectionStatus } = useStore();
  const addToast = useToastStore((s) => s.addToast);
  const [isAutoScroll, setIsAutoScroll] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const [isStarting, setIsStarting] = useState(false);

  const scrollToBottom = useCallback(() => {
    if (isAutoScroll) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [isAutoScroll]);

  useEffect(() => {
    scrollToBottom();
  }, [agent.messages, scrollToBottom]);

  const handleScroll = () => {
    const container = messagesContainerRef.current;
    if (!container) return;
    const { scrollTop, scrollHeight, clientHeight } = container;
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
    setIsAutoScroll(isNearBottom);
  };

  const handleSendMessage = async (message: string) => {
    const activeAdapter = agent.activeAdapter;
    if (!activeAdapter || agent.status === 'idle') {
      addToast("Please connect to an agent first", "info");
      return;
    }

    if (message.trim() === '/clear') {
       clearAgentMessages();
       return;
    }

    // Append user message to store (internal UI update)
    useStore.getState().appendAgentMessage({
      type: 'AGENT_MESSAGE',
      content: `> ${message}`, // Keep prefix for logic, UI will strip it
      timestamp: Date.now()
    });

    if (activeAdapter && agent.status === 'running') {
      try {
        await rcp.sendAgentMessage(activeAdapter, message);
      } catch (err) {
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
      addToast(`Initializing ${agent.activeAdapter}...`, 'info');
      try {
        const response = await rcp.startAgent(agent.activeAdapter);
        if (response.type === 'error') {
          throw new Error(response.error?.message || 'Failed to start agent');
        }
        addToast(`Agent ${agent.activeAdapter} online.`, 'success');
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        addToast(`Initialization failed: ${msg}`, 'error');
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
    if (name === 'antigravity') return 'Vision Agent';
    if (name === 'antigravity-agent') return 'Terminal Link';
    return name || 'Unselected';
  };

  const handleApproval = async (decision: boolean) => {
    if (agent.activeAdapter) {
      await rcp.sendApproval(agent.activeAdapter, decision);
    }
  };

  return (
    <div className="agent-chat animate-fade-in">
      <div className="agent-chat__header">
        <div className="agent-chat__title">
          <Bot size={18} className="text-zinc-500" />
          <span>{getFriendlyName(agent.activeAdapter)}</span>
          {agent.activeAdapter && (
            <span className="agent-chat__adapter-badge">{agent.activeAdapter}</span>
          )}
        </div>
        <div className="agent-chat__header-actions">
          <div className={`agent-chat__status ${agent.status}`}>
            <span className={`agent-chat__status-dot ${agent.status !== 'idle' ? 'active' : ''}`}></span>
            <span className="tracking-widest uppercase text-[9px] font-bold">
              {agent.status.replace('_', ' ')}
            </span>
          </div>
          <button 
            className="p-1.5 hover:bg-zinc-800 rounded-md transition-colors text-zinc-500 hover:text-zinc-100"
            onClick={() => clearAgentMessages()}
            title="Clear Buffer"
          >
            <Trash2 size={14} />
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
              {agent.activeAdapter.includes('agent') ? <TerminalIcon size={48} /> : <Bot size={48} />}
            </div>
            <h3>{getFriendlyName(agent.activeAdapter)}</h3>
            <p className="text-zinc-400">Connection to the remote agent interface is currently offline.</p>
            <button 
              className="mt-4 flex items-center gap-2 px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold transition-all shadow-lg shadow-blue-900/20" 
              onClick={handleStart}
              disabled={isStarting || connectionStatus !== 'connected'}
            >
              {isStarting ? (
                <Loader2 size={18} className="animate-spin" />
              ) : (
                <>
                  <Zap size={16} fill="currentColor" />
                  <span>INITIALIZE LINK</span>
                </>
              )}
            </button>
          </div>
        ) : agent.messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full opacity-20 pointer-events-none">
             <MessagesSquare size={64} className="mb-4" />
             <p className="font-mono text-xs uppercase tracking-widest">Awaiting interaction...</p>
          </div>
        ) : (
          agent.messages.map((msg, idx) => {
            const isUser = msg.content.startsWith('>');
            const isError = msg.content.startsWith('!');
            const content = isUser ? msg.content.slice(1).trim() : msg.content;
            
            // Check grouping logic (Option B: First in stack)
            const isSameAsLastSender = idx > 0 && (
               (agent.messages[idx-1].content.startsWith('>') === isUser) &&
               agent.messages[idx-1].type !== 'APPROVAL_REQUEST'
            );
            const showAvatar = !isSameAsLastSender;

            if (msg.type === 'APPROVAL_REQUEST') {
              return (
                <div key={idx} className="agent-chat__message-wrapper agent with-avatar">
                   <div className="agent-chat__avatar">
                     <img src={agentAvatar} alt="Agent" className="agent-chat__avatar-img" />
                   </div>
                   <div className="agent-chat__message approval animate-fade-in">
                     <div className="agent-chat__approval-title">
                       <ShieldAlert size={18} />
                       <span>AUTHORIZATION REQUIRED</span>
                     </div>
                     <div className="text-zinc-300 text-sm leading-relaxed">{content}</div>
                     {agent.status === 'awaiting_approval' && idx === agent.messages.length - 1 && (
                       <div className="agent-chat__approval-actions">
                         <button onClick={() => handleApproval(true)} className="agent-chat__approval-btn agent-chat__approval-btn--approve">
                           ACCEPT DECISION
                         </button>
                         <button onClick={() => handleApproval(false)} className="agent-chat__approval-btn agent-chat__approval-btn--reject">
                           REJECT
                         </button>
                       </div>
                     )}
                   </div>
                </div>
              );
            }

            if (content === '--- ACK ---') return null;

            return (
              <div key={idx} className={`agent-chat__message-wrapper ${isUser ? 'user' : 'agent'} ${showAvatar ? 'with-avatar' : 'no-avatar'}`}>
                <div className="agent-chat__avatar">
                  {showAvatar && (
                    isUser ? <UserAvatar /> : <img src={agentAvatar} alt="Agent" className="agent-chat__avatar-img" />
                  )}
                </div>
                <div className={`agent-chat__message ${isUser ? 'user' : isError ? 'log' : 'agent'}`}>
                  {isUser || isError ? (
                    content
                  ) : (
                    <ReactMarkdown 
                      remarkPlugins={[remarkGfm]}
                      components={{
                        p: ({children}) => <p className="mb-2 last:mb-0">{children}</p>,
                        ul: ({children}) => <ul className="list-disc ml-4 mb-2">{children}</ul>,
                        ol: ({children}) => <ol className="list-decimal ml-4 mb-2">{children}</ol>,
                        li: ({children}) => <li className="mb-1">{children}</li>,
                        code: ({children}) => <code className="bg-zinc-800 px-1.5 py-0.5 rounded text-xs font-mono">{children}</code>
                      }}
                    >
                      {content}
                    </ReactMarkdown>
                  )}
                </div>
              </div>
            );
          })
        )}
        <div ref={messagesEndRef} />
      </div>

      {!isAutoScroll && (
        <button className="agent-chat__scroll-btn" onClick={() => setIsAutoScroll(true)}>
          <ArrowDown size={16} />
        </button>
      )}

      <div className="agent-chat__input-area">
        <AiChatInput 
          onSendMessage={handleSendMessage}
          isLoading={isStarting || agent.status === 'awaiting_approval'}
          agentStatus={agent.status}
        />
      </div>
    </div>
  );
}
