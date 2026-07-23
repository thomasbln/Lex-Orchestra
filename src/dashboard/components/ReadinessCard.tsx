'use client'
import type { Readiness, ReadinessCheck } from '../lib/api'

const mono = { fontFamily: "'JetBrains Mono', monospace" } as const

// First-start status card ("Erstkontakt" honesty): rendered ONLY while the
// system is still preparing. A fully ready system never shows it, and a dead
// API is the page's apiError state's job — the card stays out of that case.
export default function ReadinessCard({ readiness }: { readiness: Readiness }) {
  if (readiness.ready) return null

  const rows: Array<{ key: 'graph' | 'database' | 'llm'; label: string; check: ReadinessCheck }> = [
    { key: 'graph', label: 'Knowledge graph', check: readiness.checks.graph },
    { key: 'database', label: 'Database schema', check: readiness.checks.database },
    { key: 'llm', label: 'Language model', check: readiness.checks.llm },
  ]

  return (
    <div style={{
      background: 'var(--bg-surface)',
      border: '1px solid var(--border-default)',
      borderRadius: '4px',
      padding: '16px 20px',
      marginBottom: '20px',
    }}>
      <div style={{ ...mono, fontSize: '12px', color: 'var(--text-primary)', fontWeight: 600, marginBottom: '10px' }}>
        ⏳ First start — system preparing
      </div>

      {rows.map(r => (
        <div key={r.key} style={{ display: 'flex', alignItems: 'baseline', gap: '10px', padding: '3px 0' }}>
          <span style={{ ...mono, fontSize: '12px', color: r.check.ok ? '#4ade80' : '#fbbf24', flexShrink: 0 }}>
            {r.check.ok ? '✓' : '⏳'}
          </span>
          <span style={{ fontSize: '12px', color: 'var(--text-secondary)', minWidth: '130px', flexShrink: 0 }}>
            {r.label}
          </span>
          <span style={{ ...mono, fontSize: '11px', color: 'var(--text-muted)' }}>
            {r.check.detail}
          </span>
        </div>
      ))}

      {!readiness.checks.llm.ok && (
        <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '10px', lineHeight: 1.5 }}>
          The language model downloads to <strong>your</strong> machine once (~10–15 min) —
          your data stays local. Scans unlock automatically when everything is ready.
          Check progress: <code style={{ ...mono, fontSize: '10px' }}>docker exec ollama ollama list</code>
        </div>
      )}
    </div>
  )
}
