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
import { useHealth } from '../../api/hooks.ts';

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

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const { data: health } = useHealth();
  const isConnected = health?.status === 'ok';

  return (
    <aside
      className={`
        flex flex-col h-screen bg-bg-secondary border-r border-border-subtle
        transition-all duration-300 shrink-0
        ${collapsed ? 'w-16' : 'w-72'}
      `}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 h-18 border-b border-border-subtle">
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
      <nav className="flex-1 overflow-y-auto py-6">
        {NAV_GROUPS.map((group) => (
          <div key={group.label} className="mb-6">
            {!collapsed && (
              <div className="overline px-5 mb-3">{group.label}</div>
            )}
            {group.items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={('end' in item && item.end) || false}
                className={({ isActive }) => `
                  flex items-center gap-3 px-5 py-3 mx-2 rounded-md
                  font-mono text-[16px] font-medium
                  transition-all duration-150
                  ${isActive
                    ? 'text-accent bg-accent-bg border-l-2 border-accent'
                    : 'text-text-secondary hover:text-text-primary hover:bg-bg-hover border-l-2 border-transparent'
                  }
                  ${collapsed ? 'justify-center mx-1 px-2' : ''}
                `}
              >
                <item.icon size={22} strokeWidth={1.5} className="shrink-0" />
                {!collapsed && <span>{item.label}</span>}
              </NavLink>
            ))}
          </div>
        ))}
      </nav>

      {/* Connection status */}
      <div className="px-4 py-3 border-t border-border-subtle">
        <div className={`flex items-center gap-2 ${collapsed ? 'justify-center' : ''}`}>
          <span
            className={`w-2 h-2 rounded-full shrink-0 ${
              isConnected ? 'bg-status-online pulse-dot' : 'bg-status-error'
            }`}
          />
          {!collapsed && (
            <span className="font-mono text-[13px] font-semibold tracking-wider uppercase text-text-secondary">
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
