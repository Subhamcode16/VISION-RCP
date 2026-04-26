import React from 'react';
import { SectionWrapper } from './ui/SectionWrapper';
import { SquareTerminal, QrCode, Globe } from 'lucide-react';

const steps = [
  {
    title: "1. Install & Connect",
    description: "Launch the Vision-RCP daemon on your host machine. One command establishes the secure bridge.",
    icon: <SquareTerminal size={32} />,
    command: "vision-rcp connect"
  },
  {
    title: "2. Authenticate",
    description: "Scan the auto-generated QR code or use the provided secure link to sync your dashboard instantly.",
    icon: <QrCode size={32} />,
    command: "Scan QR to Sync"
  },
  {
    title: "3. Orchestrate",
    description: "Your agent is now live. Monitor logs, audit flow, and direct your fleet from any browser, anywhere.",
    icon: <Globe size={32} />,
    command: "v-rcp.vercel.app"
  }
];

export const DeploymentTimeline: React.FC = () => {
  return (
    <SectionWrapper id="how-it-works" className="timeline-section py-32">
      <div className="text-center mb-24 px-4">
        <h1 className="section-header-h1">From Code to Control</h1>
        <p className="text-neutral text-lg md:text-xl max-w-2xl mx-auto">
          Deploying a remote control plane for your agent fleet has never been this seamless. No configuration, just orchestration.
        </p>
      </div>

      <div className="relative max-w-5xl mx-auto">
        {/* Connection Line */}
        <div className="absolute top-1/2 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-white/20 to-transparent hidden md:block" />

        <div className="grid grid-cols-1 md:grid-cols-3 gap-16 relative z-10">
          {steps.map((step, i) => (
            <div key={i} className="timeline-step group">
              <div className="flex flex-col items-center text-center">
                <div className="step-icon-wrapper h-20 w-20 rounded-3xl bg-white/[0.03] border border-white/10 flex items-center justify-center mb-8 group-hover:border-white/40 group-hover:bg-white/[0.08] transition-all duration-500 relative">
                    <div className="absolute inset-0 bg-white/5 blur-xl rounded-full opacity-0 group-hover:opacity-100 transition-opacity" />
                    <div className="text-white relative z-10 group-hover:scale-110 transition-transform">
                        {step.icon}
                    </div>
                </div>
                
                <h3 className="text-xl font-bold mb-4 text-white uppercase tracking-wider">{step.title}</h3>
                <p className="text-neutral text-sm leading-relaxed mb-6 px-4">
                  {step.description}
                </p>

                <div className="step-badge px-4 py-2 rounded-lg bg-white/5 border border-white/5 font-mono text-[10px] text-white/50 uppercase tracking-widest group-hover:text-white group-hover:border-white/20 transition-all">
                    {step.command}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <style>{`
        .step-icon-wrapper {
            box-shadow: 0 0 0 0 rgba(255, 255, 255, 0);
        }
        .timeline-step:hover .step-icon-wrapper {
            box-shadow: 0 0 40px -10px rgba(255, 255, 255, 0.2);
        }
      `}</style>
    </SectionWrapper>
  );
};
