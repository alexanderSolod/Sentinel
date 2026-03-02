'use client';
import { useEffect, useRef, useState } from 'react';

const steps = [
  { n: '01', label: 'Watch every trade',         desc: 'Live WebSocket feed from Polymarket. Every trade, every market.',                              color: '#ff8c00' },
  { n: '02', label: 'Spot the anomalies',         desc: 'Volume spikes, price jumps, and fresh wallets get flagged automatically.',                                   color: '#ff2020' },
  { n: '03', label: 'Check the news',             desc: 'Cross-referenced against GDELT, GDACS, ACLED, and NASA FIRMS to find what was public and when.',          color: '#33ff33' },
  { n: '04', label: 'Run the AI',                 desc: 'Mistral Small triages fast. Magistral goes deep, reasoning through motive, opportunity, and evidence.',    color: '#ff8c00' },
  { n: '05', label: 'Publish the flag',            desc: 'A structured report with evidence timeline, confidence score, and alternative explanations. Open to the public.',  color: '#ff2020' },
  { n: '06', label: 'Build the record',           desc: 'Every case enters the Sentinel Index. The first open, public database of prediction market integrity cases.',        color: '#33ff33' },
];

function StepRow({ step, i }: { step: typeof steps[0]; i: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setVisible(true); obs.disconnect(); } }, { threshold: 0.2 });
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className="flex items-start gap-6 py-8 border-b border-border-subtle"
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? 'translateX(0)' : 'translateX(-24px)',
        transition: `opacity 0.5s ease ${i * 0.08}s, transform 0.5s ease ${i * 0.08}s`,
      }}
    >
      <span className="text-2xl font-bold w-12 flex-shrink-0 tabular-nums"
        style={{ color: step.color, fontFamily: 'var(--font-mono)' }}>
        {step.n}
      </span>
      <div>
        <h3 className="text-lg font-bold text-text-primary" style={{ fontFamily: 'var(--font-mono)' }}>
          {step.label}
        </h3>
        <p className="mt-3 text-base text-text-secondary leading-[1.9]" style={{ fontFamily: 'var(--font-mono)' }}>
          {step.desc}
        </p>
      </div>
    </div>
  );
}

export default function Architecture() {
  return (
    <section id="architecture" className="relative"
      style={{ padding: 'clamp(4rem, 8vh, 6rem) clamp(2rem, 5vw, 6rem)' }}
    >
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[80%] max-w-4xl h-[1px] bg-gradient-to-r from-transparent via-border-default to-transparent" />

      <div className="relative z-10 w-full max-w-[1200px] mx-auto">
        <span className="text-xs font-bold tracking-[0.15em] uppercase text-accent" style={{ fontFamily: 'var(--font-mono)' }}>
          // Architecture
        </span>
        <div className="mt-3 w-20 h-[1px] bg-accent/40" />

        <h2 className="mt-10 font-bold text-text-primary"
          style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(2.2rem,5vw,4rem)', lineHeight: 1.1 }}>
          How it works
        </h2>

        <div className="mt-12">
          {steps.map((step, i) => <StepRow key={step.n} step={step} i={i} />)}
        </div>
      </div>
    </section>
  );
}
