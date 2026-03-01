import { motion } from 'framer-motion';
import Globe from './Globe';
import { ArrowRight, Eye } from 'lucide-react';

export default function Hero() {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden"
      style={{ padding: 'clamp(6.5rem, 12vh, 9rem) clamp(2rem, 5vw, 6rem) clamp(9rem, 16vh, 13rem)' }}
    >
      {/* Gradient overlay */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            'linear-gradient(135deg, #050508 0%, #0A0A1A 40%, #0A1020 60%, #050508 100%)',
          zIndex: 1,
          opacity: 0.7,
        }}
      />

      <div className="relative z-10 w-full max-w-[1200px] mx-auto flex flex-col lg:flex-row items-center gap-20 lg:gap-24">
        {/* Globe */}
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1, ease: [0.16, 1, 0.3, 1] }}
          className="w-full max-w-[480px] lg:max-w-[560px] flex-shrink-0"
        >
          <Globe />
        </motion.div>

        {/* Title & tagline */}
        <motion.div
          initial={{ opacity: 0, x: 40 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.8, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
          className="flex flex-col items-center lg:items-start text-center lg:text-left"
        >
          {/* Logo mark */}
          <div className="flex items-center gap-4 mb-10">
            <div className="relative">
              <Eye className="w-9 h-9 text-accent" />
              <div className="absolute inset-0 blur-lg bg-accent/30 rounded-full animate-pulse" />
            </div>
            <span
              className="text-xs font-semibold tracking-[0.2em] uppercase text-text-secondary"
              style={{ fontFamily: 'var(--font-mono)' }}
            >
              Surveillance System
            </span>
          </div>

          <h1
            className="text-6xl md:text-7xl lg:text-8xl font-bold tracking-tight leading-[1.0]"
            style={{ fontFamily: 'var(--font-display)' }}
          >
            <span className="text-text-primary">Sentinel</span>
          </h1>

          <p
            className="mt-10 text-xl md:text-2xl text-text-secondary max-w-xl"
            style={{ fontFamily: 'var(--font-mono)', lineHeight: 1.5 }}
          >
            Bloomberg for prediction markets
          </p>

          <p
            className="mt-8 text-base text-text-tertiary max-w-lg leading-[1.8]"
            style={{ fontFamily: 'var(--font-mono)' }}
          >
            AI-powered surveillance detecting information asymmetry and insider trading across prediction markets in real time.
          </p>

          <div className="mt-14 flex flex-col sm:flex-row gap-5">
            <a
              href="https://github.com/your-repo/sentinel"
              target="_blank"
              rel="noopener noreferrer"
              className="group inline-flex items-center gap-3 px-8 py-4 rounded-lg font-semibold text-sm
                         bg-accent text-bg-primary hover:bg-accent/90 transition-all duration-200
                         hover:scale-[1.02] active:scale-[0.98]"
              style={{ fontFamily: 'var(--font-mono)' }}
            >
              Try Sentinel
              <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
            </a>
            <a
              href="#what-is-sentinel"
              className="inline-flex items-center gap-3 px-8 py-4 rounded-lg font-semibold text-sm
                         border border-border-default text-text-secondary hover:text-text-primary
                         hover:border-accent/40 transition-all duration-200"
              style={{ fontFamily: 'var(--font-mono)' }}
            >
              Learn More
            </a>
          </div>

          {/* Hackathon badge */}
          <div className="mt-14 flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-accent animate-pulse" />
            <span
              className="text-xs tracking-[0.1em] text-text-tertiary uppercase"
              style={{ fontFamily: 'var(--font-mono)' }}
            >
              Built for the Mistral Global 2026 Hackathon
            </span>
          </div>
        </motion.div>
      </div>

      {/* Scroll hint */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.5, duration: 1 }}
        className="absolute bottom-12 left-1/2 -translate-x-1/2 z-10"
      >
        <div className="flex flex-col items-center gap-3">
          <span
            className="text-[10px] uppercase tracking-[0.15em] text-text-tertiary"
            style={{ fontFamily: 'var(--font-mono)' }}
          >
            Scroll
          </span>
          <motion.div
            animate={{ y: [0, 8, 0] }}
            transition={{ repeat: Infinity, duration: 1.5, ease: 'easeInOut' }}
            className="w-[1px] h-8 bg-gradient-to-b from-accent/60 to-transparent"
          />
        </div>
      </motion.div>
    </section>
  );
}
