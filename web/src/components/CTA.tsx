import { motion } from 'framer-motion';
import { ArrowRight, Github } from 'lucide-react';

export default function CTA() {
  return (
    <section id="cta" className="relative"
      style={{ padding: 'clamp(9rem, 18vh, 15rem) clamp(2rem, 5vw, 6rem)' }}
    >
      {/* Divider */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[80%] max-w-4xl h-[1px] bg-gradient-to-r from-transparent via-border-default to-transparent" />

      <div className="relative z-10 w-full max-w-[1200px] mx-auto flex flex-col items-center text-center">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-80px' }}
          transition={{ duration: 0.7 }}
        >
          <span
            className="text-xs font-semibold tracking-[0.15em] uppercase text-accent"
            style={{ fontFamily: 'var(--font-mono)' }}
          >
            // Check Us Out
          </span>
          <div className="mt-3 mx-auto w-20 h-[1px] bg-accent/40" />
        </motion.div>

        <motion.h2
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-60px' }}
          transition={{ duration: 0.6, delay: 0.15 }}
          className="mt-16 mx-auto max-w-[18ch] text-4xl md:text-5xl lg:text-6xl font-bold text-text-primary leading-[1.06] tracking-[-0.015em]"
          style={{ fontFamily: 'var(--font-display)' }}
        >
          Ready to Watch the Watchers?
        </motion.h2>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-40px' }}
          transition={{ duration: 0.6, delay: 0.25 }}
          className="mt-12 text-base md:text-lg text-text-secondary max-w-[680px] leading-[1.85]"
          style={{ fontFamily: 'var(--font-mono)' }}
        >
          Sentinel is open source. Clone the repo, add your Mistral API key, and start monitoring prediction markets for information asymmetry.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-30px' }}
          transition={{ duration: 0.6, delay: 0.35 }}
          className="mt-20"
        >
          <a
            href="https://github.com/your-repo/sentinel"
            target="_blank"
            rel="noopener noreferrer"
            className="group inline-flex items-center gap-4 px-14 py-6 rounded-2xl font-bold text-lg
                       bg-accent text-bg-primary hover:bg-accent/90 transition-all duration-200
                       hover:scale-[1.03] active:scale-[0.98]
                       shadow-[0_0_40px_rgba(0,240,255,0.15)] hover:shadow-[0_0_60px_rgba(0,240,255,0.25)]"
            style={{ fontFamily: 'var(--font-mono)' }}
          >
            <Github className="w-6 h-6" />
            Try Sentinel
            <ArrowRight className="w-6 h-6 group-hover:translate-x-1 transition-transform" />
          </a>
        </motion.div>

        {/* Hackathon attribution */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, delay: 0.5 }}
          className="mt-28"
        >
          <div className="inline-flex items-center gap-3 px-7 py-4 rounded-xl border border-border-subtle bg-bg-secondary/40">
            <div className="w-2.5 h-2.5 rounded-full bg-accent animate-pulse" />
            <span
              className="text-sm tracking-[0.06em] text-text-secondary"
              style={{ fontFamily: 'var(--font-mono)' }}
            >
              Built in 48 hours for the{' '}
              <span className="text-text-primary font-semibold">Mistral Global 2026 Hackathon</span>
            </span>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
