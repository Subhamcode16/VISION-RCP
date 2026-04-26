import React from 'react';

interface LogoProps {
  size?: number;
  showText?: boolean;
}

export const Logo: React.FC<LogoProps> = ({ size = 32, showText = false }) => {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
      <svg
        width={size}
        height={size}
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        style={{ filter: 'drop-shadow(0 0 8px rgba(59, 130, 246, 0.4))' }}
      >
        <path
          d="M20 30L50 80L80 30"
          stroke="url(#logo_grad_landing)"
          strokeWidth="12"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <circle cx="50" cy="15" r="5" fill="#3b82f6" />
        <circle cx="85" cy="85" r="4" fill="#60a5fa" />
        <circle cx="15" cy="85" r="4" fill="#60a5fa" />
        <defs>
          <linearGradient id="logo_grad_landing" x1="20" y1="30" x2="80" y2="80" gradientUnits="userSpaceOnUse">
            <stop stopColor="white" />
            <stop offset="1" stopColor="#3b82f6" />
          </linearGradient>
        </defs>
      </svg>
      {showText && (
        <span style={{ 
          fontWeight: 700, 
          fontSize: `${size * 0.6}px`, 
          letterSpacing: '-0.02em', 
          color: 'white',
          fontFamily: 'system-ui, -apple-system, sans-serif'
        }}>
          VISION-RCP
        </span>
      )}
    </div>
  );
};
