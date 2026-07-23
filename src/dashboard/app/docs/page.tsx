'use client'
import { Suspense, useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { getDocs, getDocContent, getPdfDownloadUrl, getRetrievalTraceDownloadUrl, type DocMeta, type RunMeta } from '../../lib/api'
import Sidebar from '../../components/Sidebar'

const DOC_TYPE_LABELS: Record<string, string> = {
  avv: 'AVV — Data Processing Agreement (Art. 28)',
  tom: 'TOM — Technical & Organisational Measures',
  vvt: 'VVT — Records of Processing Activities',
  dsfa: 'DSFA — Data Protection Impact Assessment',
  scc: 'SCC — Standard Contractual Clauses',
  ai_act_manifest: 'EU AI Act — Risk Manifest',
  ki_system_openai: 'AI System Documentation',
  ki_policy: 'AI Policy — Internal Directive',
  scan_report: 'Scan Report',
}

function DocRow({ doc }: { doc: DocMeta }) {
  const [expanded, setExpanded] = useState(false)
  const [content, setContent] = useState('')
  const [loading, setLoading] = useState(false)

  const label = DOC_TYPE_LABELS[doc.doc_type] ?? doc.doc_type.toUpperCase()
  const date = new Date(doc.created_at * 1000).toLocaleString('de-DE')

  const handleExpand = async () => {
    if (!expanded && !content) {
      setLoading(true)
      const c = await getDocContent(doc.filename)
      setContent(c)
      setLoading(false)
    }
    setExpanded(!expanded)
  }

  const handleDownload = async () => {
    let data = content
    if (!data) {
      data = await getDocContent(doc.filename)
      setContent(data)
    }
    const blob = new Blob(['\ufeff' + data], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = doc.filename
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div style={{
      background: 'var(--bg-surface)',
      border: '1px solid var(--border-default)',
      borderLeft: '2px solid var(--accent)',
      borderRadius: '6px',
      marginBottom: '4px',
      overflow: 'hidden',
    }}>
      <div
        onClick={handleExpand}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          padding: '10px 16px',
          cursor: 'pointer',
          minHeight: '44px',
        }}
      >
        <span style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '11px',
          fontWeight: 600,
          color: 'var(--accent)',
          minWidth: '260px',
          letterSpacing: '0.04em',
        }}>
          {label}
        </span>
        <span style={{
          fontSize: '12px',
          color: 'var(--text-muted)',
          fontFamily: "'JetBrains Mono', monospace",
          flex: 1,
        }}>
          run: {doc.run_id} · {Math.round(doc.size_bytes / 1024)}KB
        </span>
        <span style={{
          fontSize: '11px',
          color: 'var(--text-muted)',
          fontFamily: "'JetBrains Mono', monospace",
        }}>
          {date}
        </span>
        {doc.pdf_filename && (
          <a
            href={getPdfDownloadUrl(doc.pdf_filename)}
            download={doc.pdf_filename}
            onClick={(e) => e.stopPropagation()}
            style={{
              padding: '4px 12px',
              background: 'var(--accent)',
              border: '1px solid var(--accent)',
              borderRadius: '4px',
              color: '#fff',
              fontSize: '11px',
              fontFamily: "'JetBrains Mono', monospace",
              cursor: 'pointer',
              textDecoration: 'none',
            }}
          >
            ↓ PDF
          </a>
        )}
        {/* ADR-127 P5c: per-doc ↓logbook button removed — provenance lives at run
            level via the Graph-Trace (ADR-112). Doc row → [↓PDF] [↓.md]. */}
        <button
          onClick={(e) => { e.stopPropagation(); handleDownload() }}
          style={{
            padding: '4px 12px',
            background: 'rgba(74,143,255,0.08)',
            border: '1px solid var(--accent)',
            borderRadius: '4px',
            color: 'var(--accent)',
            fontSize: '11px',
            fontFamily: "'JetBrains Mono', monospace",
            cursor: 'pointer',
          }}
        >
          ↓ .md
        </button>
        <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>
          {expanded ? '▲' : '▼'}
        </span>
      </div>

      {expanded && (
        <div style={{
          borderTop: '1px solid var(--border-default)',
          padding: '16px',
          background: 'var(--bg-base)',
        }}>
          {loading ? (
            <span style={{ fontSize: '12px', color: 'var(--text-muted)', fontFamily: "'JetBrains Mono', monospace" }}>
              Loading...
            </span>
          ) : (
            <pre style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: '11px',
              color: 'var(--text-secondary)',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              margin: 0,
              maxHeight: '400px',
              overflowY: 'auto',
            }}>
              {content}
            </pre>
          )}
        </div>
      )}
    </div>
  )
}

// ADR-112: readable in-dashboard render of the per-run graph retrieval trace.
// Fetches the same JSON the download serves, renders service → query → node as
// a collapsible tree (the graph tracing stack, human-readable instead of raw JSON).
interface TraceNode { label: string; key: string; properties: Record<string, unknown>; assigned_to?: string }
interface TraceQuery { query: string; returned: TraceNode[]; via?: string }
interface TraceServiceEntry { service: { name: string; mapping_status?: string }; queries: TraceQuery[] }
interface TraceData { run_id: string; service_traces: TraceServiceEntry[]; run_level_queries: TraceQuery[] }

function nodeTitle(props: Record<string, unknown>): string {
  for (const k of ['title_de', 'title_en', 'short', 'name', 'name_de']) {
    const v = props[k]
    if (typeof v === 'string' && v) return v
  }
  return ''
}

const monoSmall = { fontFamily: "'JetBrains Mono', monospace", fontSize: '11px' } as const

function QueryBlock({ q }: { q: TraceQuery }) {
  const empty = q.returned.length === 0
  return (
    <div style={{ marginLeft: '16px', marginTop: '6px' }}>
      <div style={{ ...monoSmall, color: empty ? 'var(--text-muted)' : 'var(--text-secondary)' }}>
        {q.query} · {empty ? 'leer (Graph-Gap)' : `${q.returned.length} Nodes`}
        {q.via && <span style={{ color: 'var(--text-muted)' }}> · via {q.via}</span>}
      </div>
      {q.returned.map((n, i) => (
        <div key={i} style={{ ...monoSmall, marginLeft: '16px', marginTop: '2px', color: 'var(--text-secondary)' }}>
          <span style={{ color: 'var(--accent)' }}>[{n.label}]</span> {n.key}
          {nodeTitle(n.properties) && <span style={{ color: 'var(--text-muted)' }}> · {nodeTitle(n.properties)}</span>}
          {n.assigned_to && <span style={{ color: 'var(--text-muted)' }}> · →{n.assigned_to}</span>}
        </div>
      ))}
    </div>
  )
}

function RunTrace({ runId, runIdFull, traceFilename, editable }: { runId: string; runIdFull: string | null; traceFilename: string; editable: boolean }) {
  const [open, setOpen] = useState(false)
  const [data, setData] = useState<TraceData | null>(null)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState(false)

  const toggle = async () => {
    if (!open && !data && !err) {
      setLoading(true)
      try {
        const res = await fetch(getRetrievalTraceDownloadUrl(traceFilename))
        if (res.ok) setData(await res.json())
        else setErr(true)
      } catch {
        setErr(true)
      }
      setLoading(false)
    }
    setOpen(o => !o)
  }

  return (
    <div style={{
      background: 'var(--bg-surface)', border: '1px solid var(--border-default)',
      borderRadius: '6px', marginBottom: '16px', overflow: 'hidden',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '10px 16px' }}>
        <button
          onClick={toggle}
          style={{
            background: 'transparent', border: 'none', cursor: 'pointer', padding: 0,
            color: 'var(--text-secondary)', ...monoSmall, fontSize: '12px',
          }}
        >
          {open ? '▾' : '▸'} Graph-Trace
        </button>
        <span style={{ flex: 1, ...monoSmall, fontSize: '12px', color: 'var(--text-muted)' }}>
          Run {runId} · all Cypher queries + returned nodes of this scan
        </span>
        <a
          href={getRetrievalTraceDownloadUrl(traceFilename)}
          download={traceFilename}
          title="ADR-112 Graph-Retrieval-Trace (query-seitig, per Run) — rohes JSON inkl. aller Node-Properties"
          onClick={(e) => e.stopPropagation()}
          style={{
            flexShrink: 0, padding: '4px 12px', background: 'transparent',
            border: '1px solid var(--border-default)', borderRadius: '4px',
            color: 'var(--text-muted)', ...monoSmall, cursor: 'pointer', textDecoration: 'none',
          }}
        >
          ↓ JSON
        </a>
        {/* ADR-127 P5c/P5d: run-level "edit measures" — gated by editable_run_ids (P4.5,
            full UUIDs). Link carries the full run_id_full so the measures/rerender
            endpoints (exact UUID match) resolve directly. Only shown when editable. */}
        {editable ? (
          <Link
            href={`/docs/measures?run=${encodeURIComponent(runIdFull ?? '')}`}
            onClick={(e) => e.stopPropagation()}
            title="Edit this scan's measures"
            style={{
              flexShrink: 0, padding: '4px 12px', background: 'rgba(74,143,255,0.08)',
              border: '1px solid var(--accent)', borderRadius: '4px',
              color: 'var(--accent)', ...monoSmall, cursor: 'pointer', textDecoration: 'none',
            }}
          >
            ✎ Edit measures
          </Link>
        ) : (
          <button
            disabled
            title="Only the current scan is editable. A new scan inherits your measures automatically."
            style={{
              flexShrink: 0, padding: '4px 12px', background: 'transparent',
              border: '1px solid var(--border-default)', borderRadius: '4px',
              color: 'var(--text-muted)', ...monoSmall, cursor: 'not-allowed', opacity: 0.5,
            }}
          >
            ✎ Edit measures
          </button>
        )}
      </div>
      {open && (
        <div style={{
          borderTop: '1px solid var(--border-default)', padding: '12px 16px',
          background: 'var(--bg-base)', maxHeight: '480px', overflowY: 'auto',
        }}>
          {loading && <span style={{ ...monoSmall, color: 'var(--text-muted)' }}>Loading trace…</span>}
          {err && <span style={{ ...monoSmall, color: 'var(--text-muted)' }}>Trace konnte nicht geladen werden.</span>}
          {data && (
            <>
              {data.service_traces.map((st, i) => (
                <div key={i} style={{ marginBottom: '12px' }}>
                  <div style={{ ...monoSmall, fontSize: '12px', color: 'var(--text-primary)', fontWeight: 600 }}>
                    {st.service.name}
                    <span style={{
                      ...monoSmall, marginLeft: '8px', fontWeight: 400,
                      color: st.service.mapping_status === 'no_graph_node' ? 'var(--text-secondary)' : 'var(--text-muted)',
                    }}>
                      [{st.service.mapping_status}]
                    </span>
                  </div>
                  {st.queries.map((q, j) => <QueryBlock key={j} q={q} />)}
                </div>
              ))}
              {data.run_level_queries.length > 0 && (
                <div style={{ marginTop: '8px', paddingTop: '8px', borderTop: '1px solid var(--border-default)' }}>
                  <div style={{ ...monoSmall, color: 'var(--text-muted)' }}>run-level</div>
                  {data.run_level_queries.map((q, j) => <QueryBlock key={j} q={q} />)}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}

export default function DocsPage() {
  return (
    <Suspense fallback={<div style={{ minHeight: '100vh', background: 'var(--bg-base)' }} />}>
      <DocsContent />
    </Suspense>
  )
}

function DocsContent() {
  const searchParams = useSearchParams()
  const runIdParam = searchParams.get('run_id') || ''
  // /docs endpoint returns run_id as 8-char prefix (parsed from filename "tom_<8chars>.md").
  // Normalize URL param to same shape so client-side filter matches.
  const runIdShort = runIdParam ? runIdParam.slice(0, 8) : ''
  const [docs, setDocs] = useState<DocMeta[]>([])
  // ADR-127 P4.5: run prefixes that are editable (latest run with snapshot per project).
  const [editableRunIds, setEditableRunIds] = useState<string[]>([])
  // Scan-select metadata (row 58/part 3): project + time + status per file-run.
  const [runsMeta, setRunsMeta] = useState<RunMeta[]>([])
  const [projectFilter, setProjectFilter] = useState<string>('all')
  const [loading, setLoading] = useState(true)
  // ADR-068: initialize filter from ?run_id= URL param so /scan completion redirect
  // lands on a pre-filtered docs view.
  const [filter, setFilter] = useState<string>(runIdShort || 'all')

  useEffect(() => {
    if (runIdShort) setFilter(runIdShort)
  }, [runIdShort])

  useEffect(() => {
    getDocs().then(d => {
      setDocs(d.docs)
      setEditableRunIds(d.editable_run_ids ?? [])
      const rm = d.runs ?? []
      setRunsMeta(rm)
      // Default = newest scan (deep-link ?run_id= wins, ADR-068).
      if (!runIdShort) {
        const fileSet = new Set(d.docs.map(x => x.run_id))
        const newest = rm.map(r => r.run_id).find(id => fileSet.has(id)) ?? d.docs[0]?.run_id
        if (newest) setFilter(newest)
      }
      setLoading(false)
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const runs = Array.from(new Set(docs.map(d => d.run_id)))
  const metaById = new Map(runsMeta.map(r => [r.run_id, r]))
  // Select order: DB-known runs newest-first (runs[] is pre-sorted), then
  // file-runs without metadata (project deleted / DB down) in file-mtime order.
  const orderedRuns = [
    ...runsMeta.map(r => r.run_id).filter(id => runs.includes(id)),
    ...runs.filter(id => !metaById.has(id)),
  ]
  const projectNames = Array.from(new Set(
    runsMeta.map(r => r.project_name).filter((p): p is string => !!p)
  ))
  const visibleRuns = projectFilter === 'all'
    ? orderedRuns
    : orderedRuns.filter(id => metaById.get(id)?.project_name === projectFilter)

  const fmtTime = (iso: string): string => {
    const d = new Date(iso)
    const p = (n: number) => String(n).padStart(2, '0')
    return `${p(d.getDate())}.${p(d.getMonth() + 1)}.${d.getFullYear()}, ${p(d.getHours())}:${p(d.getMinutes())}`
  }
  const runLabel = (id: string): string => {
    const m = metaById.get(id)
    if (m) {
      const when = m.scan_time ? fmtTime(m.scan_time) : '—'
      const status = m.status === 'failed' ? ' · ⚠ failed' : ''
      const edit = editableRunIds.includes(m.run_id_full) ? ' · ✎ editable' : ''
      return `${m.project_name ?? '(project deleted)'} — ${when}${status}${edit} (${id})`
    }
    if (runsMeta.length > 0) {
      // metadata exists but not for this run → its scan_results row is gone.
      const first = docs.find(d => d.run_id === id)
      const when = first ? fmtTime(new Date(first.created_at * 1000).toISOString()) : '—'
      return `(project deleted) — ${when} (${id})`
    }
    return id // no metadata at all (DB down): no false claims, plain id.
  }

  const filtered = filter === 'all' ? docs : docs.filter(d => d.run_id === filter)
  // ADR-127 P5d: tabs/filter stay on the 8-char run_id (display); editor logic uses
  // the full UUID. All docs of a run share run_id_full — derive it for the selected run
  // (skip scan_report etc. whose run_id_full is null).
  const filterFull = filter === 'all' ? null : (filtered.find(d => d.run_id_full)?.run_id_full ?? null)

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-base)', display: 'flex' }}>
      <Sidebar />
      <main style={{ flex: 1, padding: '40px 56px', minWidth: 0 }}>

        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '28px' }}>
          <div>
            <h1 style={{
              fontSize: '32px', fontWeight: 700, color: 'var(--text-primary)',
              margin: 0, letterSpacing: '-0.02em',
            }}>
              Compliance Docs
            </h1>
            <p style={{
              fontSize: '13px', color: 'var(--text-muted)', margin: '4px 0 0',
              fontFamily: "'JetBrains Mono', monospace",
            }}>
              {loading ? '—' : `${docs.length} documents · ${runs.length} scans`}
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '16px' }}>
          {projectNames.length > 1 && (
            <select
              value={projectFilter}
              onChange={e => {
                const p = e.target.value
                setProjectFilter(p)
                if (p !== 'all') {
                  // jump to that project's newest scan so the list follows.
                  const newest = orderedRuns.find(id => metaById.get(id)?.project_name === p)
                  if (newest) setFilter(newest)
                }
              }}
              title="Projekt-Filter (nur die Scan-Auswahl, sichtbar ab 2 Projekten)"
              style={{
                padding: '4px 10px', height: '32px', borderRadius: '6px',
                border: '1px solid var(--border-strong)', background: 'var(--bg-elevated)',
                color: 'var(--text-secondary)', fontSize: '12px',
                fontFamily: "'JetBrains Mono', monospace",
              }}
            >
              <option value="all">All projects</option>
              {projectNames.map(p => <option key={p} value={p}>{p}</option>)}
            </select>
          )}
          <select
            value={filter}
            onChange={e => setFilter(e.target.value)}
            title="Select scan — newest first; ✎ marks the editable scan"
            style={{
              padding: '4px 10px', height: '32px', borderRadius: '6px', maxWidth: '560px',
              border: '1px solid var(--border-strong)', background: 'var(--bg-elevated)',
              color: 'var(--text-secondary)', fontSize: '12px',
              fontFamily: "'JetBrains Mono', monospace",
            }}
          >
            <option value="all">All scans</option>
            {visibleRuns.map(run => (
              <option key={run} value={run}>{runLabel(run)}</option>
            ))}
          </select>
        </div>

        <div style={{ height: '1px', background: 'var(--border-default)', marginBottom: '16px' }} />

        {/* ADR-112: per-run graph retrieval trace — surfaced once at run level
            (not per doc row), shown when a single run is selected. */}
        {!loading && filter !== 'all' && filtered[0]?.retrieval_trace_filename && (
          <RunTrace runId={filter} runIdFull={filterFull} traceFilename={filtered[0].retrieval_trace_filename} editable={!!filterFull && editableRunIds.includes(filterFull)} />
        )}

        {loading ? (
          <div style={{ padding: '64px 0', textAlign: 'center', fontFamily: "'JetBrains Mono', monospace", fontSize: '13px', color: 'var(--text-muted)' }}>
            Loading documents...
          </div>
        ) : filtered.length === 0 ? (
          <div style={{ padding: '80px 0', textAlign: 'center' }}>
            <p style={{ fontSize: '14px', color: 'var(--text-secondary)', margin: '0 0 8px' }}>
              No documents yet
            </p>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', fontFamily: "'JetBrains Mono', monospace" }}>
              Scan von der Projects-Seite starten
            </p>
          </div>
        ) : (
          <div>
            {filtered.map(doc => (
              <DocRow key={doc.filename} doc={doc} />
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
