import React from 'react';
import { SectionWrapper } from './ui/SectionWrapper';

const testimonials = [
  {
    name: "Alex Rivera",
    role: "Fullstack Engineer",
    text: "Managing Antigravity sessions used to be a nightmare of terminal tabs. Vision-RCP converged everything into a single, mobile-ready dashboard.",
    avatar: "AR"
  },
  {
    name: "Samantha Lee",
    role: "Security Researcher",
    text: "The Flow Audit feature is a game-changer. Finally, I can verify exactly what my autonomous agents are doing in real-time.",
    avatar: "SL"
  },
  {
    name: "Marcus Chen",
    role: "Early Access Tester",
    text: "Vision-RCP turned my local machine into a global workstation. I can deploy from the café with full confidence in my agent fleet.",
    avatar: "MC"
  }
];

export const Testimonials: React.FC = () => {
  return (
    <SectionWrapper className="testimonials-section">
      <div className="text-center mb-16 px-4">
        <h1 className="section-header-h1">What Early Testers Say</h1>
      </div>
      <div className="testimonial-grid">
        {testimonials.map((t, i) => (
          <div key={i} className="testimonial-card">
            <div className="testimonial-header">
              <div className="testimonial-avatar">{t.avatar}</div>
              <div>
                <div className="testimonial-name">{t.name}</div>
                <div className="testimonial-role">{t.role}</div>
              </div>
            </div>
            <p className="testimonial-text">"{t.text}"</p>
          </div>
        ))}
      </div>
      <style>{`
        .testimonial-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
          gap: 2rem;
          margin-top: 4rem;
        }
        .testimonial-card {
          background: rgba(17, 17, 19, 0.4);
          backdrop-filter: blur(12px);
          border: 1px solid rgba(31, 31, 35, 0.4);
          padding: 2rem;
          border-radius: 20px;
          transition: all 0.3s ease;
        }
        .testimonial-card:hover {
          transform: translateY(-5px);
          border-color: rgba(255, 255, 255, 0.3);
          background: rgba(17, 17, 19, 0.6);
        }
        .testimonial-header {
          display: flex;
          align-items: center;
          gap: 1rem;
          margin-bottom: 1.5rem;
        }
        .testimonial-avatar {
          width: 40px;
          height: 40px;
          background: #ffffff;
          border-radius: 10px;
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 700;
          color: black;
          font-size: 0.875rem;
        }
        .testimonial-name { font-weight: 600; color: white; }
        .testimonial-role { font-size: 0.75rem; color: #71717a; }
        .testimonial-text { color: #a1a1aa; line-height: 1.6; font-style: italic; }
      `}</style>
    </SectionWrapper>
  );
};
