import TypeWriter from './TypeWriter';
import Globe from './Globe';

const classifications = [
  { label: 'INSIDER',      color: '#ff2020', verdict: 'Flagged: high suspicion.', desc: 'Likely traded on non-public information' },
  { label: 'OSINT_EDGE',   color: '#33ff33', verdict: 'Flagged: likely clean.',   desc: 'Traded on public research, not insider info' },
  { label: 'FAST_REACTOR', color: '#ff8c00', verdict: 'Flagged: fast mover.',     desc: 'Reacted to breaking news within minutes' },
  { label: 'SPECULATOR',   color: '#888888', verdict: 'Clean.',                   desc: 'No information edge detected' },
];

export default function WhatIsSentinel() {
  return (
    <section id="what-is-sentinel" className="relative overflow-hidden"
      style={{ padding: 'clamp(4rem, 8vh, 6rem) clamp(2rem, 5vw, 6rem)' }}
    >
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[80%] max-w-4xl h-[1px] bg-gradient-to-r from-transparent via-border-default to-transparent" />

      {/* Globe — large, absolute right */}
      <div className="absolute top-1/2 -translate-y-1/2 right-0 pointer-events-none hidden md:block" style={{ width: '50vw' }}>
        <Globe />
      </div>

      {/* Text — left column */}
      <div className="relative z-10 w-full max-w-[1200px] mx-auto">
        <div className="max-w-full md:max-w-[52%]">

          <span className="text-xs font-bold tracking-[0.15em] uppercase text-accent" style={{ fontFamily: 'var(--font-mono)' }}>
            // What is Sentinel
          </span>
          <div className="mt-3 w-20 h-[1px] bg-accent/40" />

          <div className="mt-10">
            <TypeWriter
              text="We flag what everyone else buries."
              speed={40}
              tag="h2"
              className="text-[clamp(3rem,5.5vw,4.5rem)] font-bold leading-[1.1] text-text-primary"
            />
          </div>

          <p className="mt-8 text-base text-text-secondary leading-[1.9]" style={{ fontFamily: 'var(--font-mono)' }}>
            $9B in prediction market trading volume. Compliance teams watch it. Regulators watch it. Nobody publishes what they find.
          </p>

          <p className="mt-6 text-base text-text-secondary leading-[1.9]" style={{ fontFamily: 'var(--font-mono)' }}>
            We do.
          </p>

          <div className="mt-12 space-y-0">
            {classifications.map((cls) => (
              <div key={cls.label} className="flex flex-col sm:flex-row sm:items-baseline gap-1 sm:gap-5 py-4 border-b border-border-subtle">
                <span className="text-xs font-bold uppercase tracking-wider sm:w-28 flex-shrink-0"
                  style={{ color: cls.color, fontFamily: 'var(--font-mono)' }}>
                  {cls.label}
                </span>
                <span className="text-sm font-bold flex-shrink-0"
                  style={{ color: cls.color, fontFamily: 'var(--font-mono)' }}>
                  {cls.verdict}
                </span>
                <span className="text-sm text-text-tertiary hidden sm:block" style={{ fontFamily: 'var(--font-mono)' }}>
                  {cls.desc}
                </span>
              </div>
            ))}
          </div>

        </div>
      </div>
    </section>
  );
}
