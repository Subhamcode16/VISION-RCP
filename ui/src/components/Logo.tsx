import React from 'react';

interface LogoProps {
  size?: number;
  className?: string;
  showText?: boolean;
}

export const Logo: React.FC<LogoProps> = ({ size = 32, className = "", showText = false }) => {
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <svg
        width={size}
        height={size}
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        style={{ filter: 'drop-shadow(0 0 8px rgba(59, 130, 246, 0.4))' }}
      >
        {/* Main 'V' Shape */}
        <path
          d="M20 30L50 80L80 30"
          stroke="url(#logo_grad)"
          strokeWidth="12"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        
        {/* Orbiting Nodes */}
        <circle cx="50" cy="15" r="5" fill="#3b82f6" className="animate-pulse">
           <animate attributeName="opacity" values="1;0.4;1" dur="2s" repeatCount="indefinite" />
        </circle>
        <circle cx="85" cy="85" r="4" fill="#60a5fa">
           <animate attributeName="r" values="4;6;4" dur="3s" repeatCount="indefinite" />
        </circle>
        <circle cx="15" cy="85" r="4" fill="#60a5fa" />

        <defs>
          <linearGradient id="logo_grad" x1="20" y1="30" x2="80" y2="80" gradientUnits="userSpaceOnUse">
            <stop stopColor="white" />
            <stop offset="1" stopColor="#3b82f6" />
          </linearGradient>
        </defs>
      </svg>
      {showText && (
        <span className="font-heading font-bold tracking-tighter text-white" style={{ fontSize: `${size * 0.6}px` }}>
          VISION-RCP
        </span>
      )}
    </div>
  );
};
