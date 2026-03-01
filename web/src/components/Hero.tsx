import { motion } from 'framer-motion';
import { ArrowRight, Eye } from 'lucide-react';

export default function Hero() {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden"
      style={{ padding: 'clamp(6rem, 10vh, 8rem) clamp(2rem, 5vw, 6rem)' }}
    >
      {/* Content — centered, single column */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
        className="relative z-10 flex flex-col items-start max-w-4xl w-full"
      >
        {/* Logo mark */}
        <div className="flex items-center gap-3 mb-6">
          <Eye className="w-6 h-6 text-accent" />
          <span className="text-xs font-bold tracking-[0.22em] uppercase text-text-secondary"
            style={{ fontFamily: 'var(--font-mono)' }}>
            Surveillance System
          </span>
        </div>

        {/* Title */}
        <h1
          className="text-[clamp(6rem,16vw,13rem)] font-bold leading-[0.9] text-accent"
          style={{ fontFamily: 'var(--font-display)', textShadow: '0 0 80px rgba(255,140,0,0.2)' }}
        >
          Sentinel
        </h1>

        {/* Tagline */}
        <p className="mt-10 text-[clamp(1.2rem,2.8vw,1.8rem)] text-text-secondary max-w-3xl"
          style={{ fontFamily: 'var(--font-mono)', lineHeight: 1.7 }}>
          Prediction market surveillance exists. None of it is public.
          <span className="text-accent font-bold"> Ours is.</span>
        </p>

        {/* Crime story */}
        <p className="mt-8 text-[clamp(0.9rem,1.5vw,1.1rem)] text-text-tertiary max-w-2xl leading-[1.9]"
          style={{ fontFamily: 'var(--font-mono)' }}>
          A wallet made $340K on Polymarket 3 hours before the news broke. No one published the flag. We would have.
        </p>

        {/* Buttons */}
        <div className="mt-12 flex flex-col sm:flex-row gap-5">
          <a
            href="https://github.com/your-repo/sentinel"
            target="_blank"
            rel="noopener noreferrer"
            className="group inline-flex items-center gap-3 px-8 py-4 font-bold text-base
                       bg-accent text-bg-primary hover:bg-accent/90 transition-all duration-200"
            style={{ fontFamily: 'var(--font-mono)', boxShadow: '0 0 24px rgba(255,140,0,0.2)' }}
          >
            Try Sentinel
            <ArrowRight className="w-5 h-5 group-hover:translate-x-0.5 transition-transform" />
          </a>
          <a
            href="#what-is-sentinel"
            className="inline-flex items-center gap-3 px-8 py-4 font-bold text-base
                       border border-border-default text-text-secondary
                       hover:border-accent/50 hover:text-text-primary transition-all duration-200"
            style={{ fontFamily: 'var(--font-mono)' }}
          >
            Learn More
          </a>
        </div>

        {/* Hackathon badge */}
        <div className="mt-10 flex items-center gap-3">
          <div className="w-3 h-3 bg-accent flex-shrink-0" />
          <span className="text-sm font-bold tracking-[0.14em] uppercase text-accent"
            style={{ fontFamily: 'var(--font-mono)' }}>
            Built for the Mistral Global 2026 Hackathon
          </span>
        </div>
      </motion.div>

      {/* Scroll hint */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.5, duration: 1 }}
        className="absolute bottom-10 left-1/2 -translate-x-1/2 z-10"
      >
        <div className="flex flex-col items-center gap-2">
          <span className="text-[10px] uppercase tracking-[0.15em] text-text-tertiary"
            style={{ fontFamily: 'var(--font-mono)' }}>Scroll</span>
          <motion.div
            animate={{ y: [0, 8, 0] }}
            transition={{ repeat: Infinity, duration: 1.5, ease: 'easeInOut' }}
            className="w-[1px] h-7 bg-gradient-to-b from-accent/60 to-transparent"
          />
        </div>
      </motion.div>
    </section>
  );
}
