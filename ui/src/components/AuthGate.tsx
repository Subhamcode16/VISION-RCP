import { useState } from 'react';
import { 
  Lock, 
  Loader2, 
  Globe, 
  Cpu, 
  ChevronRight
} from 'lucide-react';
import './AuthGate.css';

interface AuthGateProps {
  onLogin: (secret: string) => Promise<void>;
  error?: string;
  mode: 'local' | 'remote';
  sessionId?: string;
  isAuthenticating: boolean;
}

export function AuthGate({ onLogin, error, mode, sessionId, isAuthenticating }: AuthGateProps) {
  const [secret, setSecret] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (secret && !isAuthenticating) {
      onLogin(secret);
    }
  };

  return (
    <div className="auth-gate">
      <div className="auth-gate__card">
        <div className="auth-gate__logo">
          <div className="auth-gate__icon">
            {mode === 'remote' ? <Globe /> : <Cpu />}
          </div>
          <h1 className="auth-gate__title">VISION-RCP</h1>
          <p className="auth-gate__subtitle">
            {mode === 'remote' ? `Session ${sessionId?.slice(0, 8)}` : 'Remote Control Protocol v2.0'}
          </p>
        </div>

        <form className="auth-gate__form" onSubmit={handleSubmit}>
          <div className="auth-gate__field">
            <label className="auth-gate__label">Secret Access Key</label>
            <div className="relative">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-600">
                <Lock size={16} />
              </span>
              <input
                className="auth-gate__input w-full pl-11"
                type="password"
                placeholder="Enter key..."
                value={secret}
                onChange={(e) => setSecret(e.target.value)}
                autoFocus
                required
              />
            </div>
          </div>

          {error && (
            <div className="auth-gate__error">
              {error}
            </div>
          )}

          <button 
            className="auth-gate__submit"
            type="submit" 
            disabled={!secret || isAuthenticating}
          >
            {isAuthenticating ? (
              <Loader2 className="animate-spin" size={20} />
            ) : (
              <div className="flex items-center gap-2">
                <span>AUTHENTICATE</span>
                <ChevronRight size={16} />
              </div>
            )}
          </button>
        </form>

        <div className="auth-gate__hint">
          {mode === 'local' ? (
            <>Running in local bridge mode. Key is defined in your <code>daemon.json</code> or system variables.</>
          ) : (
            <>Encrypted tunnel established via Vision-Relay. Your session is protected by end-to-end encryption.</>
          )}
        </div>
      </div>
    </div>
  );
}
