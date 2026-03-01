import type { ReactNode } from 'react';

interface TooltipProps {
  content: string;
  children: ReactNode;
  position?: 'top' | 'bottom';
}

export default function Tooltip({ content, children, position = 'top' }: TooltipProps) {
  const isTop = position === 'top';

  return (
    <span className="group relative inline-flex">
      {children}
      <span
        className={`absolute left-0 opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity duration-150 z-50 ${
          isTop ? 'bottom-full mb-2' : 'top-full mt-2'
        }`}
        style={{
          background: '#0a0a0a',
          border: '1px solid #ff6b0088',
          color: '#ff8c00',
          fontFamily: "'Courier New', monospace",
          fontSize: '11px',
          fontWeight: 400,
          padding: '6px 10px',
          borderRadius: '4px',
          maxWidth: '280px',
          minWidth: '180px',
          whiteSpace: 'normal',
          textTransform: 'none',
          letterSpacing: '0.02em',
          lineHeight: 1.5,
          boxShadow: '0 2px 12px rgba(0,0,0,0.6), 0 0 8px #ff6b0011',
        }}
      >
        {content}
        {/* Arrow */}
        <span
          className={`absolute left-4 ${
            isTop ? 'top-full' : 'bottom-full'
          }`}
          style={{
            width: 0,
            height: 0,
            borderLeft: '5px solid transparent',
            borderRight: '5px solid transparent',
            ...(isTop
              ? { borderTop: '5px solid #ff6b0088' }
              : { borderBottom: '5px solid #ff6b0088' }),
          }}
        />
      </span>
    </span>
  );
}
