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
      initial={{ opacity: 1 }}
      animate={{ opacity: 1 }}
      className={`panel ${span === 2 ? 'col-span-2' : ''} ${className}`}
    >
      <span className="panel-corners" />
      {title && (
        <div className="panel-header">{title}</div>
      )}
      {children}
    </motion.div>
  );
}
