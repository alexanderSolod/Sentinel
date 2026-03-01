import DotGrid from './components/DotGrid';
import Hero from './components/Hero';
import WhatIsSentinel from './components/WhatIsSentinel';
import Architecture from './components/Architecture';
import CTA from './components/CTA';
import Footer from './components/Footer';

export default function App() {
  return (
    <>
      <DotGrid />
      <main className="relative flex flex-col gap-[clamp(2.5rem,6vh,5.5rem)]" style={{ zIndex: 1 }}>
        <Hero />
        <WhatIsSentinel />
        <Architecture />
        <CTA />
        <Footer />
      </main>
    </>
  );
}
