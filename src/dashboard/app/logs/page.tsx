'use client'
import { Suspense, useEffect, useState, useCallback } from 'react'
import { useSearchParams } from 'next/navigation'
import { getLogs, getScanSignals, type LogEvent, type LogsResponse, type RunMeta, type ScanSignal } from '../../lib/api'
import Sidebar from '../../components/Sidebar'

const FILTERS = [
  { key: 'all',       label: 'All' },
  { key: 'scan',      label: 'Scan' },
  { key: 'layer1',    label: 'Layer 1 Scout' },
  { key: 'layer2',    label: 'Layer 2 Presidio' },
  { key: 'layer3',    label: 'Layer 3 LLM' },
  { key: 'cypher',    label: 'Cypher' },
  { key: 'impressum', label: 'Impressum' },
]

const EVENT_CONFIG: Record<string, { color: string; label: string }> = {
  scan_complete:       { color: 'var(--state-pass)',     label: 'SCAN COMPLETE' },
  scan_start:          { color: 'var(--text-secondary)', label: 'SCAN START' },
  layer1_complete:     { color: 'var(--text-secondary)', label: 'LAYER 1 SCOUT' },
  layer2_presidio:     { color: 'var(--state-warn)',     label: 'PRESIDIO FILTER' },
  layer2_summary:      { color: 'var(--state-warn)',     label: 'PRESIDIO SUMMARY' },
  layer3_phi4:         { color: 'var(--accent)',         label: 'LLM CLASSIFY' },
  cypher_query:        { color: 'var(--state-info)',     label: 'CYPHER QUERY' },
  cypher_result:       { color: 'var(--state-info)',     label: 'CYPHER RESULT' },
  dsfa_trigger:        { color: 'var(--state-fail)',     label: 'DSFA TRIGGER' },
  llm_reasoning:       { color: 'var(--accent)',         label: 'LLM REASONING' },
  document_generation: { color: 'var(--state-pass)',     label: 'DOC GENERATED' },
  website_extraction:  { color: 'var(--accent)',         label: 'WEBSITE SCAN' },
  impressum_discovery: { color: 'var(--text-secondary)', label: 'URL DISCOVERY' },
  impressum_scan:      { color: 'var(--text-secondary)', label: 'IMPRESSUM SCAN' },
  layer2_content_scan: { color: 'var(--state-warn)',     label: 'PRESIDIO CONTENT' },
  git_clone:           { color: 'var(--state-info)',     label: 'GIT CLONE' },
  git_delete:          { color: 'var(--text-secondary)', label: 'GIT DELETE' },
}

type CypherQueryEntry = { label: string; cypher: string; result_count: number }

function EventDetail({ event }: { event: LogEvent }) {
  const [expanded, setExpanded] = useState(false)
  const [copied, setCopied] = useState(false)
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null)
  const cfg = EVENT_CONFIG[event.event] || { color: 'var(--text-muted)', label: event.event.toUpperCase() }

  const cypherQueries = Array.isArray((event as unknown as { cypher_queries?: unknown }).cypher_queries)
    ? ((event as unknown as { cypher_queries: CypherQueryEntry[] }).cypher_queries)
    : undefined

  const handleCopyQuery = (e: React.MouseEvent) => {
    e.stopPropagation()
    e.preventDefault()
    const text = String(event.cypher ?? '')
    if (!text) return
    const fallback = () => {
      const ta = document.createElement('textarea')
      ta.value = text
      ta.style.position = 'fixed'
      ta.style.opacity = '0'
      document.body.appendChild(ta)
      ta.focus()
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
    try {
      navigator.clipboard.writeText(text)
        .then(() => { setCopied(true); setTimeout(() => setCopied(false), 2000) })
        .catch(fallback)
    } catch {
      fallback()
    }
  }

  const handleCopyQueryBlock = (e: React.MouseEvent, cypher: string, idx: number) => {
    e.stopPropagation()
    e.preventDefault()
    const fallback = () => {
      const ta = document.createElement('textarea')
      ta.value = cypher
      ta.style.position = 'fixed'
      ta.style.opacity = '0'
      document.body.appendChild(ta)
      ta.focus()
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
      setCopiedIdx(idx)
      setTimeout(() => setCopiedIdx(null), 2000)
    }
    try {
      navigator.clipboard.writeText(cypher)
        .then(() => { setCopiedIdx(idx); setTimeout(() => setCopiedIdx(null), 2000) })
        .catch(fallback)
    } catch {
      fallback()
    }
  }
  const ts = event.ts ? new Date(event.ts).toLocaleTimeString('de-DE') : ''
  const runShort = event.run_id ? String(event.run_id).slice(0, 8) : ''

  const renderSummary = () => {
    switch (event.event) {
      case 'scan_complete':
        return `Risk: ${String(event.risk ?? '\u2014').toUpperCase()} \u00b7 Findings: ${event.signals_count ?? 0} \u00b7 Docs: ${(event.doc_types as string[] | undefined)?.length ?? 0} \u00b7 DSFA: ${event.dsfa ? 'yes' : 'no'}`
      case 'layer2_presidio':
        return `${String(event.entity_type ?? '\u2014')} \u00b7 score: ${typeof event.score === 'number' ? event.score.toFixed(2) : '\u2014'} \u00b7 anonymised: ${event.anonymised ? 'YES' : 'no'}`
      case 'layer3_phi4':
        return `Task: ${event.task} \u00b7 Result: ${event.result ?? '\u2014'} \u00b7 Model: ${String(event.model ?? '').split(':')[0]}`
      case 'cypher_query':
        return `${event.query_name ?? 'query'} · ${event.result_count ?? 0} result(s) · params: [${(event.params_keys as string[] | undefined)?.join(', ') ?? ''}]`
      case 'layer1_complete':
        return `Findings: ${event.signals_count ?? 0} \u00b7 Types: ${(event.signal_types as string[] | undefined)?.join(', ') ?? '\u2014'}`
      case 'dsfa_trigger':
        return `DSFA required: ${event.value ? 'YES' : 'no'} \u00b7 ${event.reason ?? ''}`
      case 'cypher_result':
        return `${(event.doc_types as string[] | undefined)?.join(', ') || 'none'} \u00b7 ${String(event.controls_count ?? 0)} controls \u00b7 risk: ${String(event.risk_level ?? '\u2014')}`
      case 'llm_reasoning':
        return `${String(event.model ?? '')} \u00b7 ${event.service_categories ? (event.service_categories as string[]).join(', ') : '\u2014'} \u00b7 ${event.leaves_network ? 'leaves network' : 'local'}`
      case 'document_generation':
        return `${String(event.doc_type ?? '')} v${String(event.version ?? '')} \u00b7 ${String(event.file_size_bytes ?? 0)} bytes \u00b7 stays_local: ${event.stays_local ? 'YES' : 'no'}`
      case 'impressum_scan':
        return `${String(event.domain ?? '')} \u00b7 found: ${(event.fields_found as string[] | undefined)?.length ?? 0} fields \u00b7 signals: ${(event.law_signals as string[] | undefined)?.join(', ') || 'none'}`
      case 'website_extraction':
        return `Domain: ${String(event.domain ?? '')} \u00b7 Fields: ${String(event.fields_found ?? 0)} \u00b7 Signals: ${String(event.signals ?? 0)} \u00b7 Cached: ${event.cached ? 'yes' : 'no'}`
      case 'layer2_content_scan':
        return `${event.files_scanned ?? 0} files scanned \u00b7 ${event.files_with_pii ?? 0} with PII \u00b7 content_discarded: YES`
      case 'git_clone':
        return `${String(event.repo_url ?? '\u2014')} \u00b7 ${String(event.clone_path ?? '\u2014')}`
      case 'git_delete':
        return `${String(event.clone_path ?? '\u2014')} \u00b7 deleted`
      default:
        return ''
    }
  }

  return (
    <div
      style={{
        borderLeft: `2px solid ${cfg.color}`,
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-default)',
        borderLeftColor: cfg.color,
        borderLeftWidth: '2px',
        borderRadius: '6px',
        marginBottom: '4px',
        overflow: 'hidden',
        transition: 'border-color 150ms ease',
        cursor: 'pointer',
      }}
      onClick={() => setExpanded(!expanded)}
    >
      {/* Row */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        padding: '10px 16px',
        minHeight: '44px',
      }}>
        <span style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '11px',
          fontWeight: 600,
          color: cfg.color,
          minWidth: '140px',
          letterSpacing: '0.04em',
        }}>
          {cfg.label}
        </span>
        <span style={{
          fontSize: '13px',
          color: 'var(--text-secondary)',
          flex: 1,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}>
          {renderSummary() || '\u2014'}
        </span>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexShrink: 0 }}>
          {runShort && (
            <span style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: '11px',
              color: 'var(--text-muted)',
            }}>
              {runShort}
            </span>
          )}
          <span style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '11px',
            color: 'var(--text-muted)',
          }}>
            {ts}
          </span>
          <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>
            {expanded ? '\u25b2' : '\u25bc'}
          </span>
        </div>
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div style={{
          borderTop: '1px solid var(--border-default)',
          padding: '12px 16px',
          background: 'var(--bg-elevated)',
        }}>
          {/* Leaves network warning badge */}
          {Boolean(event.leaves_network) && (
            <div style={{
              padding: '6px 12px',
              marginBottom: '8px',
              background: 'rgba(245,158,11,0.08)',
              border: '1px solid rgba(245,158,11,0.3)',
              borderRadius: '4px',
              fontSize: '11px',
              color: 'var(--state-warn)',
              fontFamily: "'JetBrains Mono', monospace",
            }}>
              This step sends data outside local network — intentional, user-initiated
            </div>
          )}

          {/* Cypher query special rendering */}
          {event.event === 'cypher_query' && (
            <div style={{ marginBottom: '8px' }}>
              <div style={{
                display: 'flex', alignItems: 'center', gap: '12px',
                marginBottom: '8px',
              }}>
                <span style={{
                  fontSize: '11px', color: 'var(--text-muted)',
                  fontFamily: "'JetBrains Mono', monospace",
                }}>
                  {String(event.query_name ?? '')}
                </span>
                <span style={{
                  fontSize: '11px', color: 'var(--text-muted)',
                  fontFamily: "'JetBrains Mono', monospace",
                }}>
                  params: [{(event.params_keys as string[] | undefined)?.join(', ') ?? ''}]
                </span>
                {(!cypherQueries || cypherQueries.length === 0) && (
                  <button
                    onClick={handleCopyQuery}
                    onMouseDown={(e) => e.stopPropagation()}
                    style={{
                      marginLeft: 'auto',
                      fontSize: '11px',
                      color: copied ? 'var(--state-pass)' : 'var(--accent)',
                      background: copied ? 'rgba(34,197,94,0.08)' : 'transparent',
                      border: `1px solid ${copied ? 'var(--state-pass)' : 'var(--border-strong)'}`,
                      borderRadius: '4px',
                      padding: '2px 10px',
                      fontFamily: "'JetBrains Mono', monospace",
                      cursor: 'pointer',
                      transition: 'all 150ms ease',
                      minWidth: '88px',
                    }}
                  >
                    {copied ? '\u2713 Copied' : 'Copy Query'}
                  </button>
                )}
              </div>
              {cypherQueries && cypherQueries.length > 0 ? (
                cypherQueries.map((q, qi) => (
                  <div key={qi} style={{ marginBottom: '8px' }}>
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      marginBottom: '4px',
                    }}>
                      <span style={{
                        fontSize: '10px',
                        color: 'var(--text-muted)',
                        fontFamily: "'JetBrains Mono', monospace",
                        letterSpacing: '0.06em',
                        textTransform: 'uppercase',
                      }}>
                        {q.label} — {q.result_count} rows
                      </span>
                      <button
                        onClick={(e) => handleCopyQueryBlock(e, q.cypher, qi)}
                        onMouseDown={(e) => e.stopPropagation()}
                        style={{
                          fontSize: '10px',
                          color: copiedIdx === qi ? 'var(--state-pass)' : 'var(--text-muted)',
                          background: 'transparent',
                          border: 'none',
                          fontFamily: "'JetBrains Mono', monospace",
                          cursor: 'pointer',
                          padding: '0 4px',
                        }}
                      >
                        {copiedIdx === qi ? '\u2713' : 'copy'}
                      </button>
                    </div>
                    <pre style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: '12px',
                      color: 'var(--accent)',
                      background: 'var(--bg-base)',
                      padding: '10px 12px',
                      borderRadius: '4px',
                      border: '1px solid var(--border-default)',
                      overflowX: 'auto',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                      margin: 0,
                    }}>
                      {q.cypher}
                    </pre>
                  </div>
                ))
              ) : (
                <pre style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: '12px',
                  color: 'var(--accent)',
                  background: 'var(--bg-base)',
                  padding: '12px',
                  borderRadius: '4px',
                  border: '1px solid var(--border-default)',
                  overflowX: 'auto',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  margin: 0,
                }}>
                  {String(event.cypher ?? 'no query logged')}
                </pre>
              )}
              <div style={{
                marginTop: '8px',
                fontSize: '11px',
                color: 'var(--text-muted)',
                fontFamily: "'JetBrains Mono', monospace",
              }}>
                result_count: {String(event.result_count ?? 0)}
              </div>
            </div>
          )}

          {/* Presidio special rendering */}
          {event.event === 'layer2_presidio' && (
            <div style={{
              fontSize: '12px',
              color: 'var(--state-warn)',
              fontFamily: "'JetBrains Mono', monospace",
              background: 'var(--state-warn-muted)',
              padding: '8px 12px',
              borderRadius: '4px',
              marginBottom: '8px',
            }}>
              Raw PII values never logged -- only entity types and confidence scores (ADR-001)
            </div>
          )}

          {/* Full JSON */}
          <pre style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '11px',
            color: 'var(--text-muted)',
            margin: 0,
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-all',
          }}>
            {JSON.stringify(event, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}

export default function LogsPage() {
  return (
    <Suspense fallback={<div style={{ minHeight: '100vh', background: 'var(--bg-base)' }} />}>
      <LogsContent />
    </Suspense>
  )
}

function LogsContent() {
  const searchParams = useSearchParams()
  const runIdParam = searchParams.get('run_id') || ''
  // Backend log events store 8-char short run_id (see approve_api /logs).
  // Normalize URL param so ?run_id=<full-uuid> and pill-click (short) match.
  const runIdShort = runIdParam ? runIdParam.slice(0, 8) : ''
  const [filter, setFilter] = useState('all')
  // ADR-068: initialize from ?run_id= URL param so scan-status → logs deep links work
  const [runId, setRunId] = useState(runIdShort)
  const [data, setData] = useState<LogsResponse>({ events: [], total: 0, run_ids: [] })
  const [loading, setLoading] = useState(true)
  const [autoRefresh, setAutoRefresh] = useState(false)
  const [signals, setSignals] = useState<ScanSignal[]>([])
  const [signalsProject, setSignalsProject] = useState('')

  const fetchLogs = useCallback(async () => {
    const result = await getLogs(filter, runId)
    setData(result)
    setLoading(false)
    const hasComplete = result.events.slice(0, 10).some(e => e.event === 'scan_complete')
    setAutoRefresh(!hasComplete && result.events.length > 0)
  }, [filter, runId])

  useEffect(() => {
    setLoading(true)
    fetchLogs()
  }, [fetchLogs])

  // ADR-068: keep runId in sync with ?run_id= param (e.g. direct link from scan page)
  useEffect(() => {
    setRunId(runIdShort)
  }, [runIdShort])

  useEffect(() => {
    if (!autoRefresh) return
    const interval = setInterval(fetchLogs, 5000)
    return () => clearInterval(interval)
  }, [autoRefresh, fetchLogs])

  // Fetch persisted signals when we have events (ADR-027)
  useEffect(() => {
    const project = data.events.find(e => e.project_name)?.project_name as string | undefined
    if (!project) { setSignals([]); return }
    setSignalsProject(String(project))
    getScanSignals(String(project), 50)
      .then(d => setSignals(d.signals || []))
      .catch(() => setSignals([]))
  }, [data.events])

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-base)', display: 'flex' }}>
      <Sidebar />

      <main id="main-content" style={{ flex: 1, padding: '40px 56px', minWidth: 0 }}>

        {/* Page header */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '28px' }}>
          <div>
            <h1 style={{
              fontSize: '32px', fontWeight: 700, color: 'var(--text-primary)',
              margin: 0, letterSpacing: '-0.02em',
            }}>
              Scan Logs
            </h1>
            <p style={{
              fontSize: '13px', color: 'var(--text-muted)', margin: '4px 0 0',
              fontFamily: "'JetBrains Mono', monospace",
            }}>
              {loading ? '\u2014' : `${data.total} events`}
              {autoRefresh && ' \u00b7 live'}
            </p>
          </div>

          {/* EU AI Act badge */}
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            padding: '4px 10px',
            borderRadius: '999px',
            border: '1px solid var(--border-accent)',
            background: 'var(--accent-muted)',
            fontSize: '11px',
            color: 'var(--accent)',
            fontFamily: "'JetBrains Mono', monospace",
            fontWeight: 500,
          }}>
            EU AI Act Art. 12 -- Audit Log Active
          </div>
        </div>

        {/* Privacy banner */}
        <div style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-default)',
          borderRadius: '6px',
          padding: '10px 16px',
          marginBottom: '20px',
          fontSize: '12px',
          color: 'var(--text-muted)',
          fontFamily: "'JetBrains Mono', monospace",
        }}>
          Privacy-by-Design: Raw code, file contents, PII values, and secrets are never logged.
          Only signal types, entity categories, confidence scores, and relative file paths appear here.
        </div>

        {/* Filter bar */}
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '16px', alignItems: 'center' }}>
          {FILTERS.map(f => (
            <button
              key={f.key}
              onClick={() => { setFilter(f.key) }}
              style={{
                padding: '4px 12px',
                height: '32px',
                borderRadius: '6px',
                border: `1px solid ${filter === f.key ? 'var(--accent)' : 'var(--border-strong)'}`,
                background: filter === f.key ? 'var(--accent-muted)' : 'transparent',
                color: filter === f.key ? 'var(--accent)' : 'var(--text-muted)',
                fontSize: '12px',
                fontFamily: "'JetBrains Mono', monospace",
                cursor: 'pointer',
                transition: 'all 150ms ease',
              }}
            >
              {f.label}
            </button>
          ))}

          {/* Run selector — same label format as the /docs scan select
              (part 3 follow-up): "<project> — <time> (<id8>)", newest first.
              No status/✎ here: logs are not an edit context. */}
          {data.run_ids.length > 0 && (() => {
            const runsMeta: RunMeta[] = data.runs ?? []
            // Log events carry 8-char run ids — match on r.run_id (short), NOT
            // run_id_full (a full-UUID map matches nothing and mislabels every
            // run as "(project deleted)" — root cause of the 21:26 finding).
            const metaByShort = new Map(runsMeta.map(r => [r.run_id, r]))
            const ordered = [
              ...runsMeta.map(r => r.run_id).filter(id => data.run_ids.includes(id)),
              ...data.run_ids.filter(id => !metaByShort.has(id)),
            ]
            const fmtTime = (iso: string): string => {
              const d = new Date(iso)
              const p = (n: number) => String(n).padStart(2, '0')
              return `${p(d.getDate())}.${p(d.getMonth() + 1)}.${d.getFullYear()}, ${p(d.getHours())}:${p(d.getMinutes())}`
            }
            const runLabel = (id: string): string => {
              const m = metaByShort.get(id.slice(0, 8))
              if (m) {
                const when = m.scan_time ? fmtTime(m.scan_time) : '—'
                return `${m.project_name ?? '(project deleted)'} — ${when} (${id.slice(0, 8)})`
              }
              // metadata exists but not for this run → scan_results row is gone.
              if (runsMeta.length > 0) return `(project deleted) (${id.slice(0, 8)})`
              return `${id.slice(0, 12)}...` // no metadata at all (DB down)
            }
            return (
              <select
                value={runId}
                onChange={e => setRunId(e.target.value)}
                title="Select run — newest first"
                style={{
                  marginLeft: 'auto',
                  padding: '4px 10px',
                  height: '32px',
                  borderRadius: '6px',
                  maxWidth: '420px',
                  border: '1px solid var(--border-strong)',
                  background: 'var(--bg-elevated)',
                  color: 'var(--text-secondary)',
                  fontSize: '12px',
                  fontFamily: "'JetBrains Mono', monospace",
                  cursor: 'pointer',
                }}
              >
                <option value="">All runs</option>
                {ordered.map(id => (
                  <option key={id} value={id}>{runLabel(id)}</option>
                ))}
              </select>
            )
          })()}
        </div>

        {/* Divider */}
        <div style={{ height: '1px', background: 'var(--border-default)', marginBottom: '16px' }} />

        {/* Events */}
        {loading ? (
          <div style={{
            padding: '64px 0',
            textAlign: 'center',
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '13px',
            color: 'var(--text-muted)',
          }}>
            Loading logs...
          </div>
        ) : data.events.length === 0 ? (
          <div style={{ padding: '80px 0', textAlign: 'center' }}>
            <p style={{ fontSize: '14px', color: 'var(--text-secondary)', margin: '0 0 8px' }}>
              No scan logs yet
            </p>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', fontFamily: "'JetBrains Mono', monospace" }}>
              Run a scan from the Projects page
            </p>
          </div>
        ) : (
          <div aria-label="Event timeline" role="list">
            {data.events.map((event, i) => (
              <div key={i} role="listitem">
                <EventDetail event={event} />
              </div>
            ))}
          </div>
        )}

        {/* Signal History (ADR-027) */}
        {signals.length > 0 && (
          <div style={{ marginTop: '32px' }}>
            <div style={{
              fontSize: '10px',
              color: 'var(--text-muted)',
              fontFamily: "'JetBrains Mono', monospace",
              letterSpacing: '0.08em',
              fontWeight: 700,
              marginBottom: '12px',
              textTransform: 'uppercase',
            }}>
              Signal History — {signalsProject} — {signals.length} entries
            </div>
            <div style={{
              background: 'var(--bg-surface)',
              border: '1px solid var(--border-default)',
              borderRadius: '6px',
              overflow: 'hidden',
            }}>
              {signals.map((sig, i) => (
                <div
                  key={sig.id}
                  style={{
                    display: 'flex',
                    gap: '16px',
                    alignItems: 'baseline',
                    padding: '8px 16px',
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: '12px',
                    borderBottom: i < signals.length - 1 ? '1px solid rgba(255,255,255,0.07)' : 'none',
                  }}
                >
                  <span style={{ color: 'var(--text-muted)', width: '80px', flexShrink: 0 }}>
                    {new Date(sig.created_at).toLocaleTimeString('de-DE')}
                  </span>
                  <span style={{ color: 'var(--accent)', minWidth: '140px' }}>
                    {sig.signal_type}
                  </span>
                  <span style={{ color: 'var(--text-secondary)' }}>
                    {(sig.confidence * 100).toFixed(0)}%
                  </span>
                  <span style={{ color: 'var(--text-muted)' }}>
                    {sig.source}
                  </span>
                  {sig.evidence.length > 0 && (
                    <span style={{
                      color: 'var(--text-muted)',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      maxWidth: '240px',
                    }}>
                      {sig.evidence[0]}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
