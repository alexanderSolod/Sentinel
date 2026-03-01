import { motion } from 'framer-motion';
import {
  Radio,
  AlertTriangle,
  Newspaper,
  Cpu,
  FileText,
  Database,
  ArrowRight,
} from 'lucide-react';

const pipelineSteps = [
  {
    icon: Radio,
    label: 'Data Ingestion',
    desc: 'Real-time WebSocket stream from Polymarket trades, plus OSINT feeds from GDELT, GDACS, ACLED, NASA FIRMS',
    color: '#00F0FF',
  },
  {
    icon: AlertTriangle,
    label: 'Anomaly Detection',
    desc: 'Z-score volume spikes (>3x baseline), price jumps (>15pp), fresh wallet scoring, DBSCAN cluster analysis',
    color: '#FFB800',
  },
  {
    icon: Newspaper,
    label: 'OSINT Correlation',
    desc: 'Vector store embeddings via Mistral Embed. Temporal gap computation between trades and public signals',
    color: '#FF6B2D',
  },
  {
    icon: Cpu,
    label: '3-Stage AI Classification',
    desc: 'Stage 1: Mistral Small triage (BSS/PES scores). Stage 2: Magistral deep reasoning with Fraud Triangle. Stage 3: SAR generation',
    color: '#6366F1',
  },
  {
    icon: FileText,
    label: 'SAR Generation',
    desc: 'Structured Suspicious Activity Reports with evidence timelines, alternative explanations, and confidence scores',
    color: '#FF2D55',
  },
  {
    icon: Database,
    label: 'Sentinel Index',
    desc: 'The world\'s first open database of prediction market integrity cases with human consensus scores',
    color: '#34D399',
  },
];

const differentiators = [
  {
    title: 'Fine-Tuned Mistral Small',
    desc: '500 game-theoretic training scenarios with gold-standard examples from real insider trading events.',
  },
  {
    title: 'Temporal Gap Analysis',
    desc: 'Precisely measures the time between suspicious trades and public information release to quantify information asymmetry.',
  },
  {
    title: 'OSINT vs. Insider Distinction',
    desc: 'Goes beyond "suspicious or not" — classifies whether a trader had private info or was just a sharper analyst.',
  },
  {
    title: 'Composite Risk Scoring',
    desc: 'Weighted signals from wallet age, funding chains, cluster membership, and win rate patterns.',
  },
];

export default function Architecture() {
  return (
    <section id="architecture" className="relative"
      style={{ padding: 'clamp(8rem, 14vh, 12rem) clamp(2rem, 5vw, 6rem)' }}
    >
      {/* Divider */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[80%] max-w-4xl h-[1px] bg-gradient-to-r from-transparent via-border-default to-transparent" />

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
            // Architecture
          </span>
          <div className="mt-3 w-20 h-[1px] bg-accent/40" />
        </motion.div>

        <motion.h2
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-80px' }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="mt-10 text-3xl md:text-4xl lg:text-5xl font-bold text-text-primary"
          style={{ fontFamily: 'var(--font-display)' }}
        >
          How It Works
        </motion.h2>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-60px' }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="mt-8 text-base md:text-lg text-text-secondary max-w-[700px] leading-[1.8]"
          style={{ fontFamily: 'var(--font-mono)' }}
        >
          A six-stage pipeline processes every trade through detection, correlation, and multi-model AI classification to produce actionable intelligence.
        </motion.p>

        {/* Pipeline visualization */}
        <div className="mt-16 space-y-5">
          {pipelineSteps.map((step, i) => (
            <motion.div
              key={step.label}
              initial={{ opacity: 0, x: -30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true, margin: '-40px' }}
              transition={{ duration: 0.5, delay: i * 0.08 }}
              className="flex items-start gap-6 p-6 rounded-xl border border-border-subtle bg-bg-secondary/40
                         hover:border-border-default hover:bg-bg-hover transition-all duration-300 group"
            >
              {/* Step number + icon */}
              <div className="flex items-center gap-4 flex-shrink-0">
                <span
                  className="text-xs font-bold tracking-wider"
                  style={{ color: step.color, fontFamily: 'var(--font-mono)' }}
                >
                  {String(i + 1).padStart(2, '0')}
                </span>
                <div
                  className="w-11 h-11 rounded-xl flex items-center justify-center"
                  style={{ backgroundColor: `${step.color}12` }}
                >
                  <step.icon className="w-5 h-5" style={{ color: step.color }} strokeWidth={1.5} />
                </div>
              </div>

              <div className="flex-1 min-w-0">
                <h3
                  className="text-base font-semibold text-text-primary"
                  style={{ fontFamily: 'var(--font-display)' }}
                >
                  {step.label}
                </h3>
                <p
                  className="mt-2 text-sm text-text-secondary leading-[1.7]"
                  style={{ fontFamily: 'var(--font-mono)' }}
                >
                  {step.desc}
                </p>
              </div>

              {i < pipelineSteps.length - 1 && (
                <ArrowRight className="w-5 h-5 text-text-tertiary flex-shrink-0 mt-1 group-hover:text-accent transition-colors" />
              )}
            </motion.div>
          ))}
        </div>

        {/* What makes it unique */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-80px' }}
          transition={{ duration: 0.7, delay: 0.2 }}
          className="mt-28"
        >
          <span
            className="text-xs font-semibold tracking-[0.15em] uppercase text-text-secondary"
            style={{ fontFamily: 'var(--font-mono)' }}
          >
            What Makes It Unique
          </span>

          <div className="mt-10 grid grid-cols-1 md:grid-cols-2 gap-6">
            {differentiators.map((d, i) => (
              <motion.div
                key={d.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-40px' }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
                className="p-8 rounded-xl border border-border-subtle bg-bg-secondary/30"
              >
                <h4
                  className="text-base font-semibold text-accent"
                  style={{ fontFamily: 'var(--font-display)' }}
                >
                  {d.title}
                </h4>
                <p
                  className="mt-4 text-sm text-text-secondary leading-[1.8]"
                  style={{ fontFamily: 'var(--font-mono)' }}
                >
                  {d.desc}
                </p>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Tech stack banner */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-60px' }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="mt-20 p-8 rounded-xl border border-border-subtle bg-bg-secondary/20"
        >
          <span
            className="text-xs font-semibold tracking-[0.15em] uppercase text-text-tertiary"
            style={{ fontFamily: 'var(--font-mono)' }}
          >
            Powered By
          </span>
          <div className="mt-5 flex flex-wrap gap-4">
            {[
              'Mistral Small (Triage)',
              'Magistral (Deep Reasoning)',
              'Mistral Embed (OSINT Vectors)',
              'ChromaDB',
              'GDELT / GDACS / ACLED',
              'Polymarket WebSocket',
              'Python + SQLite',
            ].map((tech) => (
              <span
                key={tech}
                className="px-4 py-2 rounded-lg text-xs text-text-secondary border border-border-subtle bg-bg-primary/60"
                style={{ fontFamily: 'var(--font-mono)' }}
              >
                {tech}
              </span>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  );
}
