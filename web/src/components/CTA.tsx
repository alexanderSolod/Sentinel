import { ArrowRight, Github } from 'lucide-react';

export default function CTA() {
  return (
    <section id="cta" className="relative"
      style={{ padding: 'clamp(4rem, 8vh, 6rem) clamp(2rem, 5vw, 6rem)' }}
    >
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[80%] max-w-4xl h-[1px] bg-gradient-to-r from-transparent via-border-default to-transparent" />

      <div className="relative z-10 w-full max-w-[1200px] mx-auto flex flex-col items-start">
        <span className="text-xs font-bold tracking-[0.15em] uppercase text-accent" style={{ fontFamily: 'var(--font-mono)' }}>
          // Sentinel Index
        </span>
        <div className="mt-3 w-20 h-[1px] bg-accent/40" />

        <h2 className="mt-10 font-bold text-text-primary"
          style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(2.2rem,5vw,4rem)', lineHeight: 1.1 }}>
          The first open database of prediction market integrity cases.
        </h2>

        <p className="mt-8 text-base text-text-secondary max-w-2xl leading-[1.9]" style={{ fontFamily: 'var(--font-mono)' }}>
          Open source. Run it yourself or browse the public index.
        </p>

        <div className="mt-12">
          <a
            href="https://github.com/your-repo/sentinel"
            target="_blank"
            rel="noopener noreferrer"
            className="group inline-flex items-center gap-4 px-10 py-5 font-bold text-base
                       bg-accent text-bg-primary hover:bg-accent/90 transition-all duration-200"
            style={{ fontFamily: 'var(--font-mono)', boxShadow: '0 0 40px rgba(255,140,0,0.2)' }}
          >
            <Github className="w-5 h-5" />
            See a Live Case
            <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
          </a>
        </div>
      </div>
    </section>
  );
}
