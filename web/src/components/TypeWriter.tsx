import { useEffect, useRef, useState } from 'react';

interface TypeWriterProps {
  text: string;
  speed?: number;
  className?: string;
  tag?: 'h2' | 'h3' | 'p' | 'span';
}

export default function TypeWriter({
  text,
  speed = 35,
  className = '',
  tag: Tag = 'p',
}: TypeWriterProps) {
  const [displayText, setDisplayText] = useState('');
  const [started, setStarted] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !started) {
          setStarted(true);
        }
      },
      { threshold: 0.05 }
    );

    if (ref.current) {
      observer.observe(ref.current);
    }

    return () => observer.disconnect();
  }, [started]);

  useEffect(() => {
    if (!started) return;

    let i = 0;
    const interval = setInterval(() => {
      if (i < text.length) {
        setDisplayText(text.slice(0, i + 1));
        i++;
      } else {
        clearInterval(interval);
      }
    }, speed);

    return () => clearInterval(interval);
  }, [started, text, speed]);

  return (
    <div ref={ref}>
      <Tag className={className} style={{ fontFamily: 'var(--font-display)' }}>
        {displayText}
        {started && displayText.length < text.length && (
          <span className="inline-block w-[2px] h-[1em] bg-accent ml-0.5 animate-pulse align-middle" />
        )}
      </Tag>
    </div>
  );
}
