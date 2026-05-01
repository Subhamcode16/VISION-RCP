"use client";

import React from "react";
import { motion } from "framer-motion";
import { Circle } from "lucide-react";

function HeroVideo({
    badge = "Vision-RCP",
    title1 = "Control your Antigravity.",
    title2 = "Remotely.",
    children,
}: {
    badge?: string;
    title1?: string;
    title2?: string;
    children?: React.ReactNode;
}) {
    const fadeUpVariants = {
        hidden: { opacity: 0, y: 30 },
        visible: (i: number) => ({
            opacity: 1,
            y: 0,
            transition: {
                duration: 1,
                delay: 0.5 + i * 0.2,
                ease: [0.25, 0.4, 0.25, 1],
            },
        }),
    };

    return (
        <div className="relative min-h-screen w-full flex flex-col items-center bg-[#000000]">
            
            {/* 1. TEXT SECTION (Free Space) */}
            <div className="relative z-10 w-full pt-48 pb-32 px-6 md:px-12">
                <div className="max-w-7xl mx-auto text-center flex flex-col items-center">

                    {/* Badge */}
                    <motion.div
                        custom={0}
                        variants={fadeUpVariants}
                        initial="hidden"
                        animate="visible"
                        className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/[0.03] border border-white/[0.1] mb-10 backdrop-blur-md shadow-2xl"
                    >
                        <Circle className="h-2 w-2 fill-white/80 animate-pulse text-white/80" />
                        <span className="text-xs md:text-sm text-white/70 tracking-[0.2em] font-medium uppercase">
                            {badge}
                        </span>
                    </motion.div>

                    {/* Main Titles - Sleek & Impactful */}
                    <motion.div
                        custom={1}
                        variants={fadeUpVariants}
                        initial="hidden"
                        animate="visible"
                        className="mb-8"
                    >
                        <h1 className="text-5xl sm:text-7xl md:text-8xl font-bold tracking-tighter leading-[1.0] flex flex-col">
                            <span className="bg-clip-text text-transparent bg-gradient-to-b from-white via-white to-white/60 text-glow pb-2">
                                {title1}
                            </span>
                            <span className="bg-clip-text text-transparent bg-gradient-to-b from-white/90 via-white/80 to-white/40 text-glow">
                                {title2}
                            </span>
                        </h1>
                    </motion.div>

                    {/* Description */}
                    <motion.div
                        custom={2}
                        variants={fadeUpVariants}
                        initial="hidden"
                        animate="visible"
                    >
                        <p className="text-base sm:text-lg md:text-xl text-white/40 mb-12 leading-relaxed font-light tracking-wide max-w-2xl mx-auto px-4">
                            Vision-RCP is the dedicated Remote Control Plane for your Antigravity agent cluster. 
                            <span className="text-white/60 font-normal"> Orchestrate, monitor, and interact </span> 
                            from any mobile browser with zero latency.
                        </p>
                    </motion.div>

                    {/* Interactive CTAs - Layered to remain clickable */}
                    <motion.div
                        custom={3}
                        variants={fadeUpVariants}
                        initial="hidden"
                        animate="visible"
                        className="w-full relative z-50"
                    >
                        {children}
                    </motion.div>
                </div>
            </div>

            {/* 2. CINEMATIC VIDEO SECTION (Deep Integration Overlap) */}
            <div className="relative w-full -mt-56 z-20 pointer-events-none mix-blend-screen overflow-hidden">
                <div className="aspect-video w-full max-w-7xl mx-auto relative scale-110">
                    <video
                        autoPlay
                        muted
                        loop
                        playsInline
                        className="w-full h-full object-cover opacity-95"
                    >
                        <source src="/hero-bg.mp4" type="video/mp4" />
                    </video>
                    
                    {/* Advanced Seamless Blending */}
                    <div className="absolute inset-0 bg-gradient-to-b from-[#000000] via-transparent to-[#000000]" />
                    <div className="absolute inset-x-0 top-0 h-64 bg-gradient-to-b from-[#000000] to-transparent" />
                    <div className="absolute inset-x-0 bottom-0 h-64 bg-gradient-to-t from-[#000000] to-transparent" />
                    
                    {/* Subtle Side Blending */}
                    <div className="absolute inset-y-0 left-0 w-32 bg-gradient-to-r from-[#000000] to-transparent" />
                    <div className="absolute inset-y-0 right-0 w-32 bg-gradient-to-l from-[#000000] to-transparent" />
                </div>
            </div>
            
            {/* Pure Black Transition Spacer */}
            <div className="h-32 w-full bg-[#000000]" />
        </div>
    );
}

export { HeroVideo }
