'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useReadiness } from './useReadiness'

const SIDEBAR_STYLES = `
  .lex-sidebar-item {
    display: flex; align-items: center; gap: 10px;
    padding: 9px 20px; font-size: 13px; cursor: pointer;
    color: var(--text-muted); background: transparent;
    border-left: 2px solid transparent;
    text-decoration: none; transition: color 150ms ease;
  }
  .lex-sidebar-item:hover { color: var(--text-secondary); }
  .lex-sidebar-item--active {
    color: var(--text-primary) !important;
    background: rgba(74,143,255,0.08);
    border-left: 2px solid var(--accent);
  }
`

const NAV_ITEMS = [
  { label: 'Projects',   href: '/dashboard/', icon: '◫' },
  { label: 'Logs',       href: '/logs/',       icon: '⊟' },
  { label: 'Docs',       href: '/docs/',       icon: '⊡' },
  { label: 'Schema',     href: '/schema/',     icon: '◈' },
]

export default function Sidebar() {
  const pathname = usePathname()
  // Honest system dot (the old one was a hardcoded green lie): green = ready,
  // amber pulse = first-start preparation running, red = API unreachable.
  const { readiness, apiDown, loaded } = useReadiness()
  const dotColor = !loaded ? 'var(--text-muted)'
    : apiDown ? '#f87171'
    : readiness?.ready ? 'var(--state-pass)'
    : '#fbbf24'
  const dotLabel = !loaded ? 'Checking…'
    : apiDown ? 'API unreachable'
    : readiness?.ready ? 'System online'
    : 'System preparing…'
  const dotPulse = loaded && !apiDown && !readiness?.ready

  return (
    <>
    <style>{SIDEBAR_STYLES}</style>
    <aside style={{
      width: '260px',
      flexShrink: 0,
      background: 'var(--bg-surface)',
      borderRight: '1px solid var(--border-default)',
      display: 'flex',
      flexDirection: 'column',
      minHeight: '100vh',
      position: 'sticky',
      top: 0,
      alignSelf: 'flex-start',
    }}>

      {/* Logo */}
      <div style={{
        padding: '24px 24px 16px',
        borderBottom: '1px solid var(--border-default)',
      }}>
        <Link href="/dashboard/" style={{ textDecoration: 'none', display: 'block' }}>
          <svg width="220" height="32" viewBox="0 0 240 28" xmlns="http://www.w3.org/2000/svg">
            <circle cx="17" cy="6"  r="2.5" fill="#0f2040" stroke="#4a8fff" strokeWidth="0.6" opacity="0.72"/>
            <circle cx="6"  cy="18" r="2"   fill="#0f2040" stroke="#4a8fff" strokeWidth="0.5" opacity="0.62"/>
            <line x1="16" y1="8.5" x2="14" y2="11" stroke="#4a8fff" strokeWidth="0.7" opacity="0.65" strokeLinecap="round"/>
            <line x1="7"  y1="16" x2="9.5" y2="14.5" stroke="#4a8fff" strokeWidth="0.6" opacity="0.58" strokeLinecap="round"/>
            <circle cx="8" cy="8.5" r="3" fill="#185FA5" stroke="#4a8fff" strokeWidth="0.6"/>
            <circle cx="8" cy="8.5" r="1.8" fill="#4a8fff"/>
            <line x1="10.5" y1="11" x2="12.5" y2="12.5" stroke="#4a8fff" strokeWidth="1" strokeLinecap="round"/>
            <circle cx="15" cy="15" r="6.5" fill="#0d1a2e" stroke="#4a8fff" strokeWidth="0.4" opacity="0.35"/>
            <circle cx="15" cy="15" r="5"   fill="#0d1a2e" stroke="#4a8fff" strokeWidth="0.9"/>
            <circle cx="15" cy="15" r="3.4" fill="#185FA5"/>
            <circle cx="15" cy="15" r="2"   fill="#4a8fff"/>
            <line x1="17.5" y1="17.5" x2="20" y2="19.5" stroke="#4a8fff" strokeWidth="0.85" strokeLinecap="round"/>
            <circle cx="22" cy="21" r="2.8" fill="#185FA5" stroke="#4a8fff" strokeWidth="0.6"/>
            <circle cx="22" cy="21" r="1.7" fill="#4a8fff"/>
            <text x="33" y="19"
              fontFamily="ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace"
              fontSize="14" fontWeight="700" letterSpacing="0.06em" fill="#e8eaf2">
              Lex-Orchestra
            </text>
          </svg>
        </Link>
        <div style={{
          fontSize: '10px',
          color: 'var(--text-muted)',
          letterSpacing: '0.03em',
          marginTop: '8px',
          fontFamily: 'ui-monospace, monospace',
          whiteSpace: 'nowrap',
        }}>
          Open Source Compliance Infrastructure
        </div>
      </div>

      {/* Main nav */}
      <nav style={{ padding: '8px 0' }}>
        {NAV_ITEMS.map(item => {
          const active = pathname === item.href
          || pathname.startsWith(item.href + '/')
          || (item.href === '/dashboard/' && pathname.startsWith('/project/'))
          return (
            <Link
              key={item.label}
              href={item.href}
              className={`lex-sidebar-item${active ? ' lex-sidebar-item--active' : ''}`}
            >
              <span style={{ fontSize: '13px', opacity: 0.6 }}>{item.icon}</span>
              {item.label}
            </Link>
          )
        })}

      </nav>

      {/* Bottom */}
      <div style={{
        marginTop: 'auto',
        padding: '14px 20px',
        borderTop: '1px solid var(--border-default)',
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
      }}>
        <div style={{
          width: '6px', height: '6px', borderRadius: '50%',
          background: dotColor,
          flexShrink: 0,
          animation: dotPulse ? 'scan-pulse 1.5s ease-in-out infinite' : undefined,
        }} />
        <span style={{
          fontSize: '11px',
          color: 'var(--text-muted)',
          fontFamily: 'ui-monospace, monospace',
        }}>
          {dotLabel}
        </span>
      </div>
    </aside>
    </>
  )
}
