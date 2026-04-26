import React from 'react';

export const VideoDemo: React.FC = () => {
  return (
    <div className="video-demo-container">
      <div className="video-placeholder">
        <div className="play-button">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="white">
            <path d="M8 5v14l11-7z" />
          </svg>
        </div>
        <div className="video-info">
          <h3>Vision-RCP: Remote Orchestration in Action</h3>
          <p>Click to watch the demo (Placeholder)</p>
        </div>
      </div>
      <style>{`
        .video-demo-container {
          width: 100%;
          max-width: 1000px;
          margin: 4rem auto;
          aspect-ratio: 16 / 9;
          background: #18181b;
          border-radius: 20px;
          border: 1px solid #27272a;
          overflow: hidden;
          position: relative;
          cursor: pointer;
          transition: transform 0.3s ease, border-color 0.3s ease;
        }
        .video-demo-container:hover {
          transform: translateY(-4px);
          border-color: #3b82f6;
        }
        .video-placeholder {
          width: 100%;
          height: 100%;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          background: radial-gradient(circle at center, #27272a 0%, #09090b 100%);
        }
        .play-button {
          width: 80px;
          height: 80px;
          background: rgba(59, 130, 246, 0.2);
          border: 2px solid #3b82f6;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          margin-bottom: 20px;
          transition: all 0.3s ease;
        }
        .video-demo-container:hover .play-button {
          background: #3b82f6;
          transform: scale(1.1);
        }
        .video-info {
          text-align: center;
        }
        .video-info h3 {
          font-size: 1.5rem;
          margin-bottom: 0.5rem;
          color: white;
        }
        .video-info p {
          color: #a1a1aa;
        }
      `}</style>
    </div>
  );
};
