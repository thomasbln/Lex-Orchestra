'use client'
// ADR-081: Project Workspace sidebar.
// Sectioned left nav shown inside /project/[name]/[section].

import Link from 'next/link'

const SECTIONS = [
  { key: 'repos',        label: 'Repositories', icon: '⊟' },
  { key: 'company',      label: 'Company & DPO', icon: '◫' },
  { key: 'retention',    label: 'Retention',     icon: '⊡' },
  { key: 'hosting',      label: 'Hosting',       icon: '◈' },
  // 'integrations' unmounted for v1.0 (verdict 2026-07-19): all 6 catalog
  // cards took secrets without a single consumer (Firecrawl reads env, not
  // vault). Return when vault consumption is real — checklist row 57j.
  { key: 'ai',           label: 'AI details',    icon: '◐' },
  // instructing_persons had never been linked here (pre-existing gap,
  // found in the NB3 browser proof) — the section existed only via URL.
  { key: 'instructing_persons', label: 'Instructing persons', icon: '✎' },
  { key: 'scans',        label: 'Scans',         icon: '▲' },
] as const

type Props = {
  projectName: string
  activeSection: string
}

const NAV_STYLES = `
  .lex-nav-item {
    display: flex; align-items: center; gap: 8px;
    padding: 8px 20px; font-size: 12px; cursor: pointer;
    color: var(--text-muted); background: transparent;
    border-left: 2px solid transparent;
    text-decoration: none; transition: color 150ms ease;
  }
  .lex-nav-item:hover { color: var(--text-secondary); }
  .lex-nav-item--active {
    color: var(--text-primary) !important;
    background: rgba(74,143,255,0.08);
    border-left: 2px solid var(--accent);
  }
  .lex-back-link {
    font-size: 11px; color: var(--text-muted);
    text-decoration: none; font-family: ui-monospace, monospace;
    display: flex; align-items: center; gap: 4px;
    transition: color 150ms ease;
  }
  .lex-back-link:hover { color: var(--text-secondary); }
`

export default function ProjectSidebar({ projectName, activeSection }: Props) {
  return (
    <>
    <style>{NAV_STYLES}</style>
    <aside style={{
      width: '220px',
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

      {/* Back link */}
      <div style={{
        padding: '18px 20px 12px',
        borderBottom: '1px solid var(--border-default)',
      }}>
        <Link href="/dashboard" className="lex-back-link">
          ← Projects
        </Link>

        {/* Project name */}
        <div style={{
          marginTop: '10px',
          fontSize: '13px',
          fontWeight: 600,
          color: 'var(--text-primary)',
          fontFamily: 'ui-monospace, monospace',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}
        title={projectName}
        >
          {projectName}
        </div>
      </div>

      {/* Section nav */}
      <nav style={{ padding: '8px 0', flex: 1 }}>
        {SECTIONS.map(({ key, label, icon }) => {
          const active = activeSection === key
          return (
            <Link
              key={key}
              href={`/project/${encodeURIComponent(projectName)}/${key}`}
              className={`lex-nav-item${active ? ' lex-nav-item--active' : ''}`}
            >
              <span style={{ fontSize: '11px', opacity: 0.6 }}>{icon}</span>
              {label}
            </Link>
          )
        })}
      </nav>
    </aside>
    </>
  )
}
