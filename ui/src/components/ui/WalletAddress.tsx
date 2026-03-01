import { useState } from 'react';
import { Copy, Check } from 'lucide-react';
import { truncateAddress } from '../../lib/formatters.ts';

interface Props {
  address: string | null | undefined;
}

export default function WalletAddress({ address }: Props) {
  const [copied, setCopied] = useState(false);

  if (!address) return <span className="text-text-tertiary font-mono text-[13px]">—</span>;

  const handleCopy = () => {
    navigator.clipboard.writeText(address);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <span className="inline-flex items-center gap-1.5 font-mono text-[13px] text-text-secondary group">
      <span title={address}>{truncateAddress(address)}</span>
      <button
        onClick={handleCopy}
        className="opacity-0 group-hover:opacity-100 transition-opacity text-text-tertiary hover:text-accent"
      >
        {copied ? <Check size={14} /> : <Copy size={14} />}
      </button>
    </span>
  );
}
