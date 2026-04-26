import React, { useLayoutEffect, useRef } from 'react';
import gsap from 'gsap';
import './App.css';
import dashboardMockup from './assets/dashboard_mockup.png';
import { Logo } from './components/Logo';
import { VideoDemo } from './components/VideoDemo';
import { WhatItDoes } from './components/WhatItDoes';
import { TrustSignals } from './components/TrustSignals';
import { DeploymentTimeline } from './components/DeploymentTimeline';
import { Testimonials } from './components/Testimonials';
import { SetupTerminal } from './components/SetupTerminal';
import { TapedFooter } from './components/ui/footer-taped-design';

import { HeroGeometric } from './components/ui/shape-landing-hero';
import { SectionWrapper } from './components/ui/SectionWrapper';

const App: React.FC = () => {
  const mockupRef = useRef<HTMLDivElement>(null);
  const rootRef = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    const ctx = gsap.context(() => {
      const tl = gsap.timeline({ defaults: { ease: 'expo.out' } });

      tl.from('.hero-mockup-wrapper', {
        scale: 0.9,
        opacity: 0,
        y: 60,
        duration: 1.8,
        delay: 0.5,
      });

      const handleMouseMove = (e: MouseEvent) => {
        if (!mockupRef.current) return;
        const { clientX, clientY } = e;
        const { innerWidth, innerHeight } = window;
        const xPos = (clientX / innerWidth - 0.5) * 15;
        const yPos = (clientY / innerHeight - 0.5) * -15;

        gsap.to(mockupRef.current, {
          rotateY: xPos,
          rotateX: yPos,
          duration: 1,
          ease: 'power1.out',
          transformPerspective: 1000,
        });
      };

      window.addEventListener('mousemove', handleMouseMove);
      return () => window.removeEventListener('mousemove', handleMouseMove);
    }, rootRef);

    return () => ctx.revert();
  }, []);

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
        <HeroGeometric
          badge="Vision-RCP v1.0"
          title1="Control your Antigravity."
          title2="Remotely."
        >
          <div className="w-full max-w-4xl px-4 mt-8 mb-8 z-20">
            <div className="flex justify-center gap-4 mt-8">
              <a href="https://github.com/Subhamcode16/VISION-RCP" target="_blank" rel="noopener noreferrer" className="btn-primary">View on GitHub</a>
              <button onClick={scrollToSetup} className="btn-secondary">Install Now</button>
            </div>

            <div className="hero-mockup-wrapper mt-16" ref={mockupRef}>
               <div className="relative group">
                <div className="absolute -inset-1 bg-gradient-to-r from-white/20 via-white/10 to-white/5 rounded-2xl blur opacity-20 group-hover:opacity-30 transition duration-1000"></div>
                <img 
                  src={dashboardMockup} 
                  alt="Vision-RCP Dashboard Mockup" 
                  className="hero-mockup relative rounded-2xl border border-white/10 shadow-2xl bg-black" 
                />
              </div>
            </div>
          </div>
        </HeroGeometric>

        <div className="max-w-7xl mx-auto px-6">
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
        </div>

        <TapedFooter />
      </main>
    </div>
  );
};

export default App;
