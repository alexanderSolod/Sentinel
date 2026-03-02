import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  Activity,
  Users,
  ChevronLeft,
  ChevronRight,
  Eye,
  BookOpen,
} from 'lucide-react';
import { useHealth, useAnomalies, useOsint } from '../../api/hooks.ts';
import type { Anomaly, OsintEvent } from '../../api/types.ts';
import { formatRelativeTime } from '../../lib/formatters.ts';

const NAV_GROUPS = [
  {
    label: 'MONITORING',
    items: [
      { to: '/', icon: Activity, label: 'Live Monitor', end: true },
    ],
  },
  {
    label: 'COMMUNITY',
    items: [
      { to: '/arena', icon: Users, label: 'Arena' },
    ],
  },
  {
    label: 'SYSTEM',
    items: [
      { to: '/reference', icon: BookOpen, label: 'Reference' },
    ],
  },
] as const;

// ---------------------------------------------------------------------------
// Inline feed helpers
// ---------------------------------------------------------------------------

const SOURCE_COLORS: Record<string, string> = {
  gdelt: '#4a9eff',
  gdacs: '#ff4444',
  acled: '#ff8c00',
  firms: '#ffcc00',
  rss: '#33ff33',
  major_news: '#ff8c00',
  nasa_firms: '#ffcc00',
  espn_live: '#33ff33',
  weather_underground: '#4a9eff',
  noaa: '#4a9eff',
  federal_reserve: '#ffcc00',
  reuters_brussels: '#ff8c00',
  eu_commission_portal: '#4a9eff',
  '9to5mac': '#33ff33',
};

function sourceColor(source: string): string {
  return SOURCE_COLORS[source.toLowerCase()] ?? '#ff6b0088';
}

function zColor(z: number | null | undefined): string {
  if (z == null) return '#ff6b00aa';
  if (z >= 3) return '#ff2020';
  if (z >= 2) return '#ff8c00';
  return '#33ff33';
}

// ---------------------------------------------------------------------------
// Sidebar
// ---------------------------------------------------------------------------

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const { data: health } = useHealth();
  const isConnected = health?.status === 'ok';

  const POLL_MS = 5000;
  const { data: trades } = useAnomalies({ limit: 15, refreshInterval: POLL_MS });
  const { data: osint } = useOsint({ limit: 15, refreshInterval: POLL_MS });

  return (
    <aside
      className={`
        flex flex-col h-screen bg-bg-secondary border-r border-border-subtle
        transition-all duration-300 shrink-0
        ${collapsed ? 'w-16' : 'w-80'}
      `}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 h-18 border-b border-border-subtle shrink-0">
        <div className="relative shrink-0">
          <Eye size={24} className="text-accent pulse-dot" />
        </div>
        {!collapsed && (
          <span className="font-mono font-bold text-xl tracking-[0.15em] text-text-primary">
            SENTINEL
          </span>
        )}
      </div>

      {/* Navigation */}
      <nav className="py-4 shrink-0">
        {NAV_GROUPS.map((group) => (
          <div key={group.label} className="mb-3">
            {!collapsed && (
              <div className="overline px-5 mb-2">{group.label}</div>
            )}
            {group.items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={('end' in item && item.end) || false}
                className={({ isActive }) => `
                  flex items-center gap-3 px-5 py-2 mx-2 rounded-md
                  font-mono text-[14px] font-medium
                  transition-all duration-150
                  ${isActive
                    ? 'text-accent bg-accent-bg border-l-2 border-accent'
                    : 'text-text-secondary hover:text-text-primary hover:bg-bg-hover border-l-2 border-transparent'
                  }
                  ${collapsed ? 'justify-center mx-1 px-2' : ''}
                `}
              >
                <item.icon size={18} strokeWidth={1.5} className="shrink-0" />
                {!collapsed && <span>{item.label}</span>}
              </NavLink>
            ))}
          </div>
        ))}
      </nav>

      {/* ---- Feeds (only when expanded) ---- */}
      {!collapsed && (
        <div className="flex-1 flex flex-col min-h-0 border-t border-border-subtle">
          {/* Trade Feed */}
          <div className="flex-1 min-h-0 flex flex-col border-b border-border-subtle">
            <div className="overline px-4 py-2 shrink-0">Polymarket Feed</div>
            <div className="flex-1 overflow-y-auto">
              {trades?.items?.length ? (
                trades.items.map((t: Anomaly, i: number) => (
                  <div key={t.event_id} className={`px-4 py-1.5 ${i % 2 === 0 ? '' : 'bg-bg-tertiary'}`}>
                    <div className="flex items-center gap-2">
                      <span
                        className="font-mono text-[11px] text-text-primary truncate flex-1"
                        title={t.market_name ?? ''}
                      >
                        {t.market_name
                          ? t.market_name.length > 28
                            ? t.market_name.slice(0, 28) + '...'
                            : t.market_name
                          : '—'}
                      </span>
                      <span className="font-mono text-[10px] text-text-tertiary whitespace-nowrap">
                        {formatRelativeTime(t.timestamp)}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 font-mono text-[10px]">
                      {t.wallet_address && (
                        <span className="text-text-tertiary">
                          {t.wallet_address.slice(0, 6)}...{t.wallet_address.slice(-4)}
                        </span>
                      )}
                      {t.trade_size != null && (
                        <span className="text-text-secondary">
                          ${t.trade_size.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                        </span>
                      )}
                      {t.z_score != null && (
                        <span className="font-semibold" style={{ color: zColor(t.z_score) }}>
                          z={t.z_score.toFixed(1)}
                        </span>
                      )}
                    </div>
                  </div>
                ))
              ) : (
                <div className="px-4 py-6 text-center font-mono text-[10px] text-text-tertiary">
                  No trades yet
                </div>
              )}
            </div>
          </div>

          {/* OSINT Feed */}
          <div className="flex-1 min-h-0 flex flex-col">
            <div className="overline px-4 py-2 shrink-0">RSS / OSINT Feed</div>
            <div className="flex-1 overflow-y-auto">
              {osint?.items?.length ? (
                osint.items.map((e: OsintEvent, i: number) => (
                  <div key={e.event_id} className={`px-4 py-1.5 ${i % 2 === 0 ? '' : 'bg-bg-tertiary'}`}>
                    <div className="flex items-center gap-2 mb-0.5">
                      <span
                        className="font-mono text-[9px] font-bold uppercase px-1 py-px rounded shrink-0"
                        style={{
                          color: sourceColor(e.source),
                          backgroundColor: sourceColor(e.source) + '18',
                          border: `1px solid ${sourceColor(e.source)}33`,
                        }}
                      >
                        {e.source}
                      </span>
                      {e.category && (
                        <span className="font-mono text-[9px] text-text-tertiary uppercase">
                          {e.category}
                        </span>
                      )}
                      <span className="font-mono text-[10px] text-text-tertiary whitespace-nowrap ml-auto">
                        {formatRelativeTime(e.timestamp)}
                      </span>
                    </div>
                    <p
                      className="font-mono text-[11px] text-text-secondary leading-snug"
                      style={{ textTransform: 'none' }}
                    >
                      {e.headline.length > 60 ? e.headline.slice(0, 60) + '...' : e.headline}
                    </p>
                  </div>
                ))
              ) : (
                <div className="px-4 py-6 text-center font-mono text-[10px] text-text-tertiary">
                  No OSINT events yet
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Connection status */}
      <div className="px-4 py-3 border-t border-border-subtle shrink-0">
        <div className={`flex items-center gap-2 ${collapsed ? 'justify-center' : ''}`}>
          <span
            className={`w-2 h-2 rounded-full shrink-0 ${
              isConnected ? 'bg-status-online pulse-dot' : 'bg-status-error'
            }`}
          />
          {!collapsed && (
            <span className="font-mono text-[11px] font-semibold tracking-wider uppercase text-text-secondary">
              {isConnected ? 'Connected' : 'Offline'}
            </span>
          )}
        </div>
      </div>

      {/* Collapse toggle */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center justify-center h-10 border-t border-border-subtle text-text-tertiary hover:text-text-primary transition-colors"
      >
        {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
      </button>
    </aside>
  );
}
