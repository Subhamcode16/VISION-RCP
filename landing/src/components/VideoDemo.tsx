import React, { useRef, useState, useEffect } from 'react';

export const VideoDemo: React.FC = () => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (videoRef.current) {
            if (entry.isIntersecting) {
              videoRef.current.play().catch((err) => {
                console.warn("Autoplay was prevented:", err);
              });
              setIsPlaying(true);
            } else {
              videoRef.current.pause();
              setIsPlaying(false);
            }
          }
        });
      },
      { threshold: 0.4 } // Trigger when 40% of the component is visible
    );

    if (containerRef.current) {
      observer.observe(containerRef.current);
    }

    return () => {
      if (containerRef.current) {
        observer.unobserve(containerRef.current);
      }
    };
  }, []);

  const togglePlay = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  return (
    <div ref={containerRef} className="video-demo-container group" onClick={togglePlay}>
      <div className="video-inner shadow-2xl shadow-blue-500/10">
        <video 
          ref={videoRef}
          className="w-full h-full object-cover"
          poster="/videos/demo-video-poster.jpg"
          loop
          playsInline
          muted // Required for autoplay in most browsers
        >
          <source src="/videos/demo-video.mp4" type="video/mp4" />
          Your browser does not support the video tag.
        </video>
        
        {!isPlaying && (
          <div className="video-overlay absolute inset-0 flex flex-col items-center justify-center bg-black/40 backdrop-blur-[2px] transition-all duration-500 group-hover:bg-black/20">
            <div className="play-button-outer flex items-center justify-center w-24 h-24 rounded-full border border-white/20 bg-white/10 backdrop-blur-md transition-all duration-300 group-hover:scale-110 group-hover:border-blue-500/50 group-hover:bg-blue-500/20">
              <div className="play-button-inner flex items-center justify-center w-16 h-16 rounded-full bg-white text-black transition-all duration-300 group-hover:bg-blue-500 group-hover:text-white">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M8 5v14l11-7z" />
                </svg>
              </div>
            </div>
            <div className="mt-8 text-center">
              <h3 className="text-2xl font-bold text-white mb-2 tracking-tight">Vision-RCP in Action</h3>
              <p className="text-white/60 font-medium">Click to see the orchestration bridge live</p>
            </div>
          </div>
        )}

        {isPlaying && (
          <div className="absolute bottom-6 right-6 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
             <div className="px-4 py-2 rounded-full bg-black/60 backdrop-blur-md border border-white/10 text-xs font-mono text-white/80">
               LIVE RECORDING • 1080P
             </div>
          </div>
        )}
      </div>

      <style>{`
        .video-demo-container {
          width: 100%;
          max-width: 1100px;
          margin: 0 auto;
          position: relative;
          cursor: pointer;
        }
        .video-inner {
          width: 100%;
          aspect-ratio: 16 / 9;
          background: #000;
          border-radius: 24px;
          border: 1px solid rgba(255, 255, 255, 0.08);
          overflow: hidden;
          position: relative;
          transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .video-demo-container:hover .video-inner {
          border-color: rgba(59, 130, 246, 0.4);
          transform: scale(1.01);
        }
        .play-button-outer {
          box-shadow: 0 0 40px rgba(0, 0, 0, 0.3);
        }
      `}</style>
    </div>
  );
};


