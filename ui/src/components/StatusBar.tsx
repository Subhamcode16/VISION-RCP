import { useStore } from '../lib/store';
import { 
  Wifi, 
  WifiOff, 
  Activity, 
  Hash, 
  Clock,
  ShieldCheck,
  Globe
} from 'lucide-react';
import './StatusBar.css';

export function StatusBar() {
  const { session, connectionStatus, systemInfo } = useStore();
  const isRemote = !!session?.sessionId;
  const cpu = systemInfo?.cpu_percent || 0;
  const ram = systemInfo ? (systemInfo.memory_used / (1024 * 1024)) : 0;

  return (
    <div className="status-bar animate-fade-in">
      <div className="status-bar__left">
        <div className="status-bar__item">
          {connectionStatus === 'connected' ? (
            <Wifi size={12} className="text-emerald-500" />
          ) : (
            <WifiOff size={12} className="text-red-500" />
          )}
          <span className="uppercase">{connectionStatus}</span>
        </div>
        <div className="status-bar__item">
          {isRemote ? <Globe size={12} /> : <ShieldCheck size={12} />}
          <span>{isRemote ? 'REMOTE_RELAY' : 'LOCAL_HOST'}</span>
        </div>
      </div>

      <div className="status-bar__center">
        <div className="status-bar__item">
           <Activity size={12} className="text-zinc-600" />
           <span>CPU: {cpu.toFixed(1)}%</span>
        </div>
        <div className="status-bar__item">
           <Hash size={12} className="text-zinc-600" />
           <span>MEM: {ram.toFixed(0)}MB</span>
        </div>
      </div>

      <div className="status-bar__right">
        <div className="status-bar__item">
          <Clock size={12} />
          <span>v2.0.4-STABLE</span>
        </div>
      </div>
    </div>
  );
}
