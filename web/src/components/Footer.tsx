import { Eye } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="relative border-t border-border-subtle"
      style={{ padding: '2.5rem clamp(2rem, 5vw, 6rem)' }}
    >
      <div className="relative z-10 w-full max-w-[1200px] mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="flex items-center gap-3">
          <Eye className="w-5 h-5 text-accent" />
          <span
            className="text-sm font-bold tracking-[0.15em] uppercase text-text-secondary"
            style={{ fontFamily: 'var(--font-mono)' }}
          >
            Sentinel
          </span>
        </div>

        <p
          className="text-xs text-text-tertiary"
          style={{ fontFamily: 'var(--font-mono)' }}
        >
          AI-Powered Prediction Market Surveillance &middot; Mistral Global Hackathon 2026
        </p>
      </div>
    </footer>
  );
}
