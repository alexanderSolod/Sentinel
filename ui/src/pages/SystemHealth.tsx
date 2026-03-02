import { motion } from 'framer-motion';
import { useAnomalies, useOsint } from '../api/hooks.ts';
import type { Anomaly, OsintEvent } from '../api/types.ts';
import Card from '../components/ui/Card.tsx';
import WalletAddress from '../components/ui/WalletAddress.tsx';
import Tooltip from '../components/ui/Tooltip.tsx';
import Skeleton from '../components/ui/Skeleton.tsx';
import { formatRelativeTime } from '../lib/formatters.ts';

// ---------------------------------------------------------------------------
// Source badge colors
// ---------------------------------------------------------------------------

const SOURCE_COLORS: Record<string, string> = {
  gdelt: '#4a9eff',
  gdacs: '#ff4444',
  acled: '#ff8c00',
  firms: '#ffcc00',
  rss: '#33ff33',
  nasa_firms: '#ffcc00',
};

function sourceColor(source: string): string {
  return SOURCE_COLORS[source.toLowerCase()] ?? '#ff8c00';
}

// ---------------------------------------------------------------------------
// Z-score color
// ---------------------------------------------------------------------------

function zScoreColor(z: number | null | undefined): string {
  if (z == null) return '#ff6b00aa';
  if (z >= 3) return '#ff2020';
  if (z >= 2) return '#ff8c00';
  return '#33ff33';
}

// ---------------------------------------------------------------------------
// Trade row
// ---------------------------------------------------------------------------

function TradeRow({ trade, idx }: { trade: Anomaly; idx: number }) {
  const marketName = trade.market_name ?? 'Unknown';
  const truncated = marketName.length > 35 ? marketName.slice(0, 35) + '...' : marketName;

  return (
    <div
      className={`px-4 py-2.5 ${idx % 2 === 0 ? 'bg-bg-primary' : ''}`}
    >
      <div className="flex items-center gap-3 mb-1">
        {marketName.length > 35 ? (
          <Tooltip content={marketName} position="bottom">
            <span className="font-mono text-xs text-text-primary truncate flex-1 cursor-help">
              {truncated}
            </span>
          </Tooltip>
        ) : (
          <span className="font-mono text-xs text-text-primary truncate flex-1">
            {truncated}
          </span>
        )}
        <span className="font-mono text-[11px] text-text-tertiary whitespace-nowrap">
          {formatRelativeTime(trade.timestamp)}
        </span>
      </div>
      <div className="flex items-center gap-4 text-[11px] font-mono">
        {trade.wallet_address && (
          <WalletAddress address={trade.wallet_address} />
        )}
        {trade.trade_size != null && (
          <span className="text-text-secondary">
            ${trade.trade_size.toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </span>
        )}
        {trade.price_change != null && (
          <span className={trade.price_change > 0 ? 'text-status-online' : 'text-text-secondary'}>
            {trade.price_change > 0 ? '+' : ''}{(trade.price_change * 100).toFixed(1)}%
          </span>
        )}
        {trade.z_score != null && (
          <span className="font-semibold" style={{ color: zScoreColor(trade.z_score) }}>
            z={trade.z_score.toFixed(2)}
          </span>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// OSINT row
// ---------------------------------------------------------------------------

function OsintRow({ event, idx }: { event: OsintEvent; idx: number }) {
  const color = sourceColor(event.source);

  return (
    <div
      className={`px-4 py-2.5 ${idx % 2 === 0 ? 'bg-bg-primary' : ''}`}
    >
      <div className="flex items-center gap-2 mb-1">
        <span
          className="font-mono text-[10px] font-bold uppercase px-1.5 py-0.5 rounded shrink-0"
          style={{
            color,
            backgroundColor: color + '18',
            border: `1px solid ${color}44`,
          }}
        >
          {event.source}
        </span>
        {event.category && (
          <span className="font-mono text-[10px] text-text-tertiary uppercase">
            {event.category}
          </span>
        )}
        <span className="font-mono text-[11px] text-text-tertiary whitespace-nowrap ml-auto">
          {formatRelativeTime(event.timestamp)}
        </span>
      </div>
      <p
        className="font-mono text-xs text-text-secondary leading-relaxed"
        style={{ textTransform: 'none' }}
      >
        {event.headline}
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// SystemHealth page
// ---------------------------------------------------------------------------

export default function SystemHealth() {
  const POLL_MS = 5000;

  const { data: trades, loading: tradesLoading } = useAnomalies({
    limit: 40,
    refreshInterval: POLL_MS,
  });
  const { data: osint, loading: osintLoading } = useOsint({
    limit: 40,
    refreshInterval: POLL_MS,
  });

  return (
    <div className="space-y-6">
      {/* ---- Page Title ---- */}
      <div>
        <p className="overline mb-1">// SYSTEM HEALTH</p>
        <h1 className="font-display text-2xl font-bold text-text-primary">
          System Health
        </h1>
      </div>

      {/* ---- Two-Column Feed ---- */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* ---- Trade Feed ---- */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <Card title="TRADE FEED">
            <p
              className="font-mono text-xs text-text-tertiary mb-3 leading-relaxed"
              style={{ textTransform: 'none' }}
            >
              Raw trades ingested from Polymarket. Shows market, wallet, trade size,
              price movement, and z-score before AI classification.
            </p>
            <div className="max-h-[70vh] overflow-y-auto -mx-5">
              {tradesLoading ? (
                Array.from({ length: 8 }).map((_, i) => (
                  <div key={i} className="px-4 py-3 space-y-2">
                    <Skeleton className="h-3 w-3/4" />
                    <Skeleton className="h-2.5 w-1/2" />
                  </div>
                ))
              ) : !trades?.items?.length ? (
                <div className="px-4 py-14 text-center text-text-tertiary font-mono text-xs">
                  No trades ingested yet
                </div>
              ) : (
                trades.items.map((t: Anomaly, idx: number) => (
                  <TradeRow key={t.event_id} trade={t} idx={idx} />
                ))
              )}
            </div>
            {trades && (
              <div className="mt-2 font-mono text-[11px] text-text-tertiary">
                {trades.total} total trades
              </div>
            )}
          </Card>
        </motion.div>

        {/* ---- OSINT Feed ---- */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.05 }}
        >
          <Card title="OSINT FEED">
            <p
              className="font-mono text-xs text-text-tertiary mb-3 leading-relaxed"
              style={{ textTransform: 'none' }}
            >
              Intelligence signals from GDELT, GDACS, ACLED, NASA FIRMS, and RSS news.
              Correlated against trades to detect information asymmetry.
            </p>
            <div className="max-h-[70vh] overflow-y-auto -mx-5">
              {osintLoading ? (
                Array.from({ length: 8 }).map((_, i) => (
                  <div key={i} className="px-4 py-3 space-y-2">
                    <Skeleton className="h-3 w-2/3" />
                    <Skeleton className="h-2.5 w-full" />
                  </div>
                ))
              ) : !osint?.items?.length ? (
                <div className="px-4 py-14 text-center text-text-tertiary font-mono text-xs">
                  No OSINT events yet
                </div>
              ) : (
                osint.items.map((e: OsintEvent, idx: number) => (
                  <OsintRow key={e.event_id} event={e} idx={idx} />
                ))
              )}
            </div>
            {osint && (
              <div className="mt-2 font-mono text-[11px] text-text-tertiary">
                {osint.total} total events
              </div>
            )}
          </Card>
        </motion.div>
      </div>
    </div>
  );
}
