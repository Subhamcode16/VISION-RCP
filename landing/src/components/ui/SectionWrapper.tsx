import React from 'react';
import { motion } from 'framer-motion';
import NeuralBackground from './flow-field-background';
import { cn } from '@/lib/utils';

interface SectionWrapperProps {
  children: React.ReactNode;
  className?: string;
  id?: string;
  particleColor?: string;
}

export const SectionWrapper: React.FC<SectionWrapperProps> = ({ 
  children, 
  className, 
  id,
  particleColor = "#ffffff" 
}) => {
  return (
    <section 
      id={id} 
      className={cn("relative overflow-hidden w-full", className)}
      style={{ padding: '8rem 0' }}
    >
      {/* Background Layer */}
      <NeuralBackground 
        color={particleColor} 
        trailOpacity={0.1}
        speed={0.5}
      />
      
      {/* Content Layer */}
      <motion.div
        initial={{ opacity: 0, y: 40 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-100px" }}
        transition={{ duration: 0.8, ease: "easeOut" }}
        className="relative z-10 max-w-[1200px] mx-auto px-8"
      >
        {children}
      </motion.div>
    </section>
  );
};
