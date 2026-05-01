import React, { useRef } from 'react';
import './App.css';
import { Logo } from './components/Logo';
import { VideoDemo } from './components/VideoDemo';
import { WhatItDoes } from './components/WhatItDoes';
import { TrustSignals } from './components/TrustSignals';
import { DeploymentTimeline } from './components/DeploymentTimeline';
import { Testimonials } from './components/Testimonials';
import { SetupTerminal } from './components/SetupTerminal';
import { TapedFooter } from './components/ui/footer-taped-design';

import { HeroVideo } from './components/ui/HeroVideo';
import { SectionWrapper } from './components/ui/SectionWrapper';

const App: React.FC = () => {
  const rootRef = useRef<HTMLDivElement>(null);

  const scrollToSetup = () => {
    const element = document.getElementById('setup');
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const dashboardUrl = "http://localhost:5173";

  return (
    <div className="landing-container bg-[#030303] min-h-screen text-white font-sans scroll-smooth" ref={rootRef}>
      <nav className="nav-bar fixed top-0 w-full z-[100] border-b border-white/5 bg-black/60 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto flex justify-between items-center px-6 py-4">
          <Logo size={36} showText={true} />
          <a href={dashboardUrl} className="btn-secondary">Open Dashboard</a>
        </div>
      </nav>

      <main className="relative">
        <HeroVideo
          badge="Vision-RCP v1.0"
          title1="Control your Antigravity."
          title2="Remotely."
        >
          <div className="flex flex-col sm:flex-row items-center justify-center gap-6 mt-12 mb-10 relative z-50">
            <a href="https://github.com/Subhamcode16/VISION-RCP" target="_blank" rel="noopener noreferrer" className="btn-primary scale-110 shadow-[0_0_20px_rgba(255,255,255,0.15)]">View on GitHub</a>
            <button onClick={scrollToSetup} className="btn-secondary scale-110 backdrop-blur-md">Install Now</button>
          </div>
        </HeroVideo>

        <WhatItDoes />
        
        <TrustSignals />

        <DeploymentTimeline />

        <SectionWrapper>
          <div className="text-center mb-16 px-4">
            <h1 className="section-header-h1">See it in Action</h1>
            <p className="text-neutral text-lg md:text-xl max-w-2xl mx-auto">Experience the power of low-latency remote control with our hardware-grade demonstration.</p>
          </div>
          <VideoDemo />
        </SectionWrapper>

        <Testimonials />

        <SectionWrapper id="setup">
          <div className="text-center mb-16 px-4">
            <h1 className="section-header-h1">Ready to Deploy?</h1>
            <p className="text-neutral text-lg md:text-xl max-w-2xl mx-auto">Install the CLI agent on your host machine to begin remote orchestration.</p>
          </div>
          <SetupTerminal />
        </SectionWrapper>

        <TapedFooter />
      </main>

    </div>
  );
};

export default App;
