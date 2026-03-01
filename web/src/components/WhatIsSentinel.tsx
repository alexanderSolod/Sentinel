import { motion } from 'framer-motion';
import TypeWriter from './TypeWriter';
import { Shield, Search, Brain, Users } from 'lucide-react';

const classifications = [
  {
    label: 'INSIDER',
    color: '#FF2D55',
    desc: 'Trade based on material non-public information',
    quadrant: 'High BSS / Low PES',
  },
  {
    label: 'OSINT_EDGE',
    color: '#FF6B2D',
    desc: 'Superior public intelligence gathering',
    quadrant: 'Low BSS / High PES',
  },
  {
    label: 'FAST_REACTOR',
    color: '#FFB800',
    desc: 'Quick reaction to breaking news',
    quadrant: 'Low BSS / High PES',
  },
  {
    label: 'SPECULATOR',
    color: '#34D399',
    desc: 'Normal speculation, no edge detected',
    quadrant: 'Low BSS / Low PES',
  },
];

export default function WhatIsSentinel() {
  return (
    <section id="what-is-sentinel" className="relative"
      style={{ padding: 'clamp(8rem, 14vh, 12rem) clamp(2rem, 5vw, 6rem)' }}
    >
      <div className="relative z-10 w-full max-w-[1200px] mx-auto">
        {/* Section label */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-100px' }}
          transition={{ duration: 0.6 }}
        >
          <span
            className="text-xs font-semibold tracking-[0.15em] uppercase text-accent"
            style={{ fontFamily: 'var(--font-mono)' }}
          >
            // What is Sentinel
          </span>
          <div className="mt-3 w-20 h-[1px] bg-accent/40" />
        </motion.div>

        {/* Typed heading — BIG */}
        <div className="mt-12">
          <TypeWriter
            text="We combine OSINT data with state-of-the-art AI methods to flag potential insider trading on prediction markets."
            speed={25}
            tag="h2"
            className="text-3xl md:text-4xl lg:text-5xl font-bold leading-[1.2] text-text-primary max-w-[900px]"
          />
        </div>

        {/* Description */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-80px' }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="mt-14 text-base md:text-lg text-text-secondary max-w-[700px] leading-[1.8]"
          style={{ fontFamily: 'var(--font-mono)' }}
        >
          Prediction markets are becoming the world's real-time truth layer. But nobody is watching
          the watchers. Nobody can tell the difference between someone with classified intel and
          someone who just reads flight-tracking data better than you. Sentinel changes that.
        </motion.p>

        {/* Feature highlights */}
        <div className="mt-28 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {[
            { icon: Shield, title: 'Real-Time Detection', desc: 'Continuous monitoring of Polymarket for volume spikes and price dislocations' },
            { icon: Search, title: 'OSINT Correlation', desc: 'Cross-references trades with GDELT, GDACS, ACLED, and NASA FIRMS data' },
            { icon: Brain, title: 'AI Classification', desc: '3-stage pipeline: fast triage, deep reasoning, and SAR generation' },
            { icon: Users, title: 'Human-in-the-Loop', desc: 'Arena voting system for crowd-validated ground truth' },
          ].map((item, i) => (
            <motion.div
              key={item.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-50px' }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              className="group p-7 rounded-xl border border-border-subtle bg-bg-secondary/60
                         hover:border-border-default hover:bg-bg-hover transition-all duration-300"
            >
              <item.icon className="w-6 h-6 text-accent mb-5" strokeWidth={1.5} />
              <h3
                className="text-base font-semibold text-text-primary mb-3"
                style={{ fontFamily: 'var(--font-display)' }}
              >
                {item.title}
              </h3>
              <p
                className="text-sm text-text-secondary leading-[1.7]"
                style={{ fontFamily: 'var(--font-mono)' }}
              >
                {item.desc}
              </p>
            </motion.div>
          ))}
        </div>

        {/* Classification grid */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-80px' }}
          transition={{ duration: 0.7, delay: 0.2 }}
          className="mt-36"
        >
          <span
            className="text-xs font-semibold tracking-[0.15em] uppercase text-text-secondary"
            style={{ fontFamily: 'var(--font-mono)' }}
          >
            Four Classification Types
          </span>

          <div className="mt-10 grid grid-cols-1 sm:grid-cols-2 gap-5">
            {classifications.map((cls) => (
              <div
                key={cls.label}
                className="flex items-start gap-5 p-6 rounded-xl border border-border-subtle bg-bg-secondary/40
                           hover:border-border-default transition-all duration-200"
              >
                <div className="flex-shrink-0 mt-1">
                  <span
                    className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold uppercase tracking-wider"
                    style={{
                      color: cls.color,
                      backgroundColor: `${cls.color}0F`,
                      fontFamily: 'var(--font-mono)',
                    }}
                  >
                    <span
                      className="w-2 h-2 rounded-full"
                      style={{ backgroundColor: cls.color }}
                    />
                    {cls.label}
                  </span>
                </div>
                <div>
                  <p
                    className="text-base text-text-primary leading-[1.6]"
                    style={{ fontFamily: 'var(--font-mono)' }}
                  >
                    {cls.desc}
                  </p>
                  <p
                    className="mt-2 text-xs text-text-tertiary"
                    style={{ fontFamily: 'var(--font-mono)' }}
                  >
                    {cls.quadrant}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  );
}
