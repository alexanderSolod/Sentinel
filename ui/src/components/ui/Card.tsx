import { motion } from 'framer-motion';
import type { ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  title?: string;
  className?: string;
  span?: 1 | 2;
}

export default function Card({ children, title, className = '', span = 1 }: CardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
      className={`
        bg-bg-secondary border border-border-subtle rounded-lg p-5
        hover:border-border-default transition-colors duration-200
        ${span === 2 ? 'col-span-2' : ''}
        ${className}
      `}
    >
      {title && (
        <div className="overline mb-4 pb-3 border-b border-border-subtle flex items-center justify-between">
          {title}
        </div>
      )}
      {children}
    </motion.div>
  );
}
