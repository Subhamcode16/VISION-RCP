import React from 'react';
import { Shield, Lock, EyeOff, Terminal } from 'lucide-react';
import { SectionWrapper } from './ui/SectionWrapper';

export const TrustSignals: React.FC = () => {
  return (
    <SectionWrapper id="trust" className="trust-signals-section">
      <div className="text-center mb-16 px-4">
        <h1 className="section-header-h1">Trust in your Agent</h1>
        <p className="text-neutral text-lg md:text-xl max-w-2xl mx-auto">
          Vision-RCP is built on a zero-compromise security architecture. We don't just protect your connection; we respect your data ownership.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mt-12">
        <div className="trust-card p-10 rounded-[32px] border border-white/5 bg-white/[0.02] backdrop-blur-xl relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-8 opacity-10 group-hover:opacity-20 transition-opacity">
            <Shield size={120} />
          </div>
          <div className="relative z-10">
            <div className="h-12 w-12 rounded-xl bg-white flex items-center justify-center mb-6">
              <Lock className="text-black" size={24} />
            </div>
            <h3 className="text-2xl font-bold mb-4 text-white">Security by Design</h3>
            <p className="text-neutral leading-relaxed mb-6">
              Every command is authenticated via <strong>HMAC-SHA256</strong> signed JWTs. Our outbound-only WSS tunnel means you never have to open inbound firewall ports.
            </p>
            <ul className="space-y-3">
              <li className="flex items-center gap-3 text-sm text-white/60">
                <div className="h-1.5 w-1.5 rounded-full bg-white/40" />
                End-to-End TLS 1.3 Encryption
              </li>
              <li className="flex items-center gap-3 text-sm text-white/60">
                <div className="h-1.5 w-1.5 rounded-full bg-white/40" />
                Automatic Secret Key Rotation
              </li>
              <li className="flex items-center gap-3 text-sm text-white/60">
                <div className="h-1.5 w-1.5 rounded-full bg-white/40" />
                Hardware-Level Process Isolation
              </li>
            </ul>
          </div>
        </div>

        <div className="trust-card p-10 rounded-[32px] border border-white/5 bg-white/[0.02] backdrop-blur-xl relative overflow-hidden group">
           <div className="absolute top-0 right-0 p-8 opacity-10 group-hover:opacity-20 transition-opacity">
            <EyeOff size={120} />
          </div>
          <div className="relative z-10">
            <div className="h-12 w-12 rounded-xl bg-white flex items-center justify-center mb-6">
              <Terminal className="text-black" size={24} />
            </div>
            <h3 className="text-2xl font-bold mb-4 text-white">Privacy Guarantee</h3>
            <p className="text-neutral leading-relaxed mb-6">
              Vision-RCP is <strong>Local-First</strong>. We providing the orchestration bridge, but your agent logs and sensitive data never persist on our relay infrastructure.
            </p>
             <ul className="space-y-3">
              <li className="flex items-center gap-3 text-sm text-white/60">
                <div className="h-1.5 w-1.5 rounded-full bg-white/40" />
                Zero Cloud Storage Policy
              </li>
              <li className="flex items-center gap-3 text-sm text-white/60">
                <div className="h-1.5 w-1.5 rounded-full bg-white/40" />
                Encrypted Peer Handshakes
              </li>
              <li className="flex items-center gap-3 text-sm text-white/60">
                <div className="h-1.5 w-1.5 rounded-full bg-white/40" />
                Audit Logs Stored Locally
              </li>
            </ul>
          </div>
        </div>
      </div>

      <style>{`
        .trust-card {
            transition: all 0.4s cubic-bezier(0.23, 1, 0.32, 1);
        }
        .trust-card:hover {
            border-color: rgba(255, 255, 255, 0.2);
            transform: translateY(-8px);
            background: rgba(255, 255, 255, 0.04);
            box-shadow: 0 40px 80px -20px rgba(0, 0, 0, 0.8);
        }
      `}</style>
    </SectionWrapper>
  );
};
