import { useState, useRef, useEffect } from 'react';

interface SelectOption {
  value: string;
  label: string;
}

interface SelectProps {
  value: string;
  onChange: (value: string) => void;
  options: SelectOption[];
  className?: string;
}

export default function Select({ value, onChange, options, className = '' }: SelectProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const selected = options.find(o => o.value === value) ?? options[0];

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  return (
    <div ref={ref} className={`relative ${className}`} style={{ minWidth: 180 }}>
      {/* Trigger */}
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          width: '100%',
          background: '#111111',
          border: '1px solid #ff8c0088',
          color: '#ff8c00',
          fontFamily: 'Courier New, monospace',
          fontSize: 11,
          fontWeight: 700,
          letterSpacing: '0.12em',
          textTransform: 'uppercase',
          padding: '6px 32px 6px 10px',
          cursor: 'pointer',
          textAlign: 'left',
          position: 'relative',
          textShadow: '0 0 8px #ff6b0066',
        }}
      >
        {selected.label}
        {/* Arrow */}
        <span style={{
          position: 'absolute',
          right: 10,
          top: '50%',
          transform: open ? 'translateY(-50%) scaleY(-1)' : 'translateY(-50%)',
          color: '#ff6b00aa',
          fontSize: 10,
          lineHeight: 1,
          transition: 'transform 0.1s',
        }}>▼</span>
      </button>

      {/* Dropdown */}
      {open && (
        <div style={{
          position: 'absolute',
          top: '100%',
          left: 0,
          right: 0,
          background: '#0a0a0a',
          border: '1px solid #ff8c0088',
          borderTop: 'none',
          zIndex: 1000,
        }}>
          {options.map(opt => (
            <div
              key={opt.value}
              onClick={() => { onChange(opt.value); setOpen(false); }}
              style={{
                padding: '7px 10px',
                fontFamily: 'Courier New, monospace',
                fontSize: 11,
                fontWeight: opt.value === value ? 700 : 400,
                letterSpacing: '0.12em',
                textTransform: 'uppercase',
                color: opt.value === value ? '#ff8c00' : '#ff6b00aa',
                background: opt.value === value ? '#ff6b0018' : 'transparent',
                cursor: 'pointer',
                textShadow: opt.value === value ? '0 0 8px #ff6b0066' : 'none',
                borderBottom: '1px solid #ff6b0022',
              }}
              onMouseEnter={e => (e.currentTarget.style.background = '#ff6b0022')}
              onMouseLeave={e => (e.currentTarget.style.background = opt.value === value ? '#ff6b0018' : 'transparent')}
            >
              {opt.value === value && <span style={{ marginRight: 6, color: '#ff8c00' }}>▶</span>}
              {opt.label}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
