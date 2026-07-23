'use client'
import { useEffect, useState } from 'react'
import {
  getProjects, getScanSignalsSummary, getDeletePreview, deleteProject,
  API_BASE,
  type ProjectSummary, type ScanSignalsSummary, type DeletePreview,
} from '../../lib/api'
import Sidebar from '../../components/Sidebar'
import ConfirmDialog from '../../components/ConfirmDialog'
import ReadinessCard from '../../components/ReadinessCard'
import { useReadiness } from '../../components/useReadiness'

export default function DashboardPage() {
  const [projects, setProjects] = useState<ProjectSummary[]>([])
  const [loading, setLoading] = useState(true)
  // F24: a thrown fetch (CORS block, stack down) must NOT render as
  // "No projects configured" — that is a false statement. Track it.
  const [apiError, setApiError] = useState(false)
  const [summaries, setSummaries] = useState<Record<string, ScanSignalsSummary>>({})
  // First-start readiness (status card above the table; polls until ready)
  const { readiness } = useReadiness()

  // ADR-125 — project deletion modal state
  const [target, setTarget] = useState<ProjectSummary | null>(null)
  const [preview, setPreview] = useState<DeletePreview | null>(null)
  const [previewError, setPreviewError] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  function openDelete(p: ProjectSummary) {
    setTarget(p)
    setPreview(null)
    setPreviewError(null)
    setDeleteError(null)
    getDeletePreview(p.project_name)
      .then(setPreview)
      .catch(() => setPreviewError('Vorschau konnte nicht geladen werden.'))
  }

  function closeDelete() {
    if (deleting) return
    setTarget(null)
    setPreview(null)
    setPreviewError(null)
    setDeleteError(null)
  }

  async function confirmDelete() {
    if (!target) return
    setDeleting(true)
    setDeleteError(null)
    try {
      await deleteProject(target.project_name)
      setProjects(prev => prev.filter(p => p.project_name !== target.project_name))
      setTarget(null)
      setPreview(null)
    } catch {
      setDeleteError('Delete failed. Please try again.')
    } finally {
      setDeleting(false)
    }
  }

  useEffect(() => {
    getProjects()
      .then(setProjects)
      // Sibling fetches (per-project summaries) share the same origin and API,
      // so this one catch surfaces the whole failure class for the start page.
      .catch(() => setApiError(true))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (projects.length === 0) return
    projects.forEach(p => {
      getScanSignalsSummary(p.project_name)
        .then(s => setSummaries(prev => ({ ...prev, [p.project_name]: s })))
        .catch(() => {})
    })
  }, [projects])

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-base)', display: 'flex' }}>
      <Sidebar />

      {/* Center content */}
      <main id="main-content" style={{ flex: 1, padding: '40px 56px', minWidth: 0 }}>

        {/* Page header */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '28px' }}>
          <div>
            <h1 style={{
              fontSize: '32px', fontWeight: 700, color: 'var(--text-primary)',
              margin: 0, letterSpacing: '-0.02em',
            }}>
              Projects
            </h1>
            <p style={{
              margin: '8px 0 0', fontSize: '13px', color: 'var(--text-muted)',
              fontFamily: 'ui-monospace, monospace',
              display: 'flex', alignItems: 'center', gap: '8px',
            }}>
              <span style={{
                width: '6px', height: '6px', borderRadius: '50%',
                background: 'var(--accent)', display: 'inline-block',
              }} />
              {loading ? '\u2014' : apiError ? 'API unreachable' : `${projects.length} configured`}
            </p>
          </div>
          <a href="/setup/" style={{
            background: 'var(--accent)',
            color: 'white',
            height: '40px',
            padding: '0 18px',
            borderRadius: '6px',
            fontSize: '13px',
            fontWeight: 500,
            textDecoration: 'none',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            transition: 'background 150ms ease',
          }}
          onMouseEnter={e => { e.currentTarget.style.background = 'var(--accent-hover)' }}
          onMouseLeave={e => { e.currentTarget.style.background = 'var(--accent)' }}
          >
            + New project
          </a>
        </div>

        {/* First-start readiness card — only while preparing; apiError leads */}
        {!apiError && readiness && <ReadinessCard readiness={readiness} />}

        {/* Table */}
        <div style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-default)',
          borderRadius: '6px',
          overflow: 'hidden',
        }}>

          {/* Column headers */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 160px 1fr 100px',
            padding: '0 20px',
            height: '36px',
            alignItems: 'center',
            borderBottom: '1px solid var(--border-default)',
          }}>
            {['PROJECT NAME', 'LAST SCAN', 'REPOSITORY', ''].map(col => (
              <span key={col} style={{
                fontSize: '10px',
                fontWeight: 700,
                color: 'var(--text-muted)',
                letterSpacing: '0.08em',
              }}>{col}</span>
            ))}
          </div>

          {/* Rows */}
          {loading ? (
            <div style={{
              padding: '48px 20px',
              textAlign: 'center',
              fontFamily: 'ui-monospace, monospace',
              fontSize: '13px',
              color: 'var(--text-muted)',
            }}
            aria-busy="true"
            aria-label="Loading projects"
            >
              Loading...
            </div>
          ) : apiError ? (
            <div style={{ padding: '64px 20px', textAlign: 'center' }}>
              <p style={{ fontSize: '14px', color: 'var(--text-secondary)', margin: '0 0 8px' }}>
                API not reachable at{' '}
                <span style={{ fontFamily: 'ui-monospace, monospace' }}>{API_BASE}</span>
                {' '}&mdash; is the stack running?
              </p>
              <p style={{
                fontSize: '13px', color: 'var(--text-muted)', margin: 0,
                fontFamily: 'ui-monospace, monospace',
              }}>
                See docs/setup/docker.md (start, CORS &amp; troubleshooting)
              </p>
            </div>
          ) : projects.length === 0 ? (
            <div style={{ padding: '64px 20px', textAlign: 'center' }}>
              <p style={{ fontSize: '14px', color: 'var(--text-secondary)', margin: '0 0 8px' }}>
                No projects configured
              </p>
              <a href="/setup/" style={{
                fontSize: '13px',
                color: 'var(--accent)',
                textDecoration: 'none',
                fontFamily: 'ui-monospace, monospace',
              }}>
                &rarr; Set up your first project
              </a>
            </div>
          ) : (
            projects.map((p, index) => (
              <div key={p.project_name} style={{
                display: 'grid',
                gridTemplateColumns: '1fr 160px 1fr 100px',
                padding: '0 20px',
                height: '54px',
                alignItems: 'center',
                borderBottom: index < projects.length - 1
                  ? '1px solid rgba(255,255,255,0.07)'
                  : 'none',
                transition: 'background 150ms ease',
              }}
              onMouseEnter={e => { e.currentTarget.style.background = 'var(--bg-elevated)' }}
              onMouseLeave={e => { e.currentTarget.style.background = 'transparent' }}
              >
                {/* Project Name */}
                <div>
                  <div style={{
                    fontWeight: 500,
                    fontSize: '14px',
                    color: 'var(--text-primary)',
                    fontFamily: 'ui-monospace, monospace',
                  }}>
                    {p.project_name}
                  </div>
                  {p.company_name && (
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
                      {p.company_name}
                    </div>
                  )}
                </div>

                {/* Last Scan */}
                <div style={{
                  fontSize: '12px',
                  color: 'var(--text-muted)',
                  fontFamily: 'ui-monospace, monospace',
                }}>
                  {summaries[p.project_name]?.last_scan_at
                    ? <>
                        {new Date(summaries[p.project_name].last_scan_at!).toLocaleDateString('de-DE', {
                          day: '2-digit', month: '2-digit', year: 'numeric',
                          hour: '2-digit', minute: '2-digit',
                        })}
                        {summaries[p.project_name].signals_count > 0 && (
                          <span style={{ color: 'var(--text-muted)', marginLeft: '6px', fontSize: '11px' }}>
                            {summaries[p.project_name].signals_count} signals
                          </span>
                        )}
                      </>
                    : '\u2014'
                  }
                </div>

                {/* Repository */}
                <div style={{
                  fontSize: '12px',
                  color: 'var(--text-muted)',
                  fontFamily: 'ui-monospace, monospace',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}>
                  {p.repo_url?.replace('https://github.com/', '') || '\u2014'}
                </div>

                {/* Actions: open workspace + delete */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '12px' }}>
                  <a href={`/project/${encodeURIComponent(p.project_name)}`} style={{
                    fontSize: '12px',
                    color: 'var(--text-muted)',
                    textDecoration: 'none',
                    fontFamily: 'ui-monospace, monospace',
                    transition: 'color 150ms ease',
                  }}
                  onMouseEnter={e => { e.currentTarget.style.color = 'var(--accent)' }}
                  onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-muted)' }}
                  >
                    open &rarr;
                  </a>
                  <button
                    type="button"
                    className="row-delete-btn"
                    aria-label={`Delete project ${p.project_name}`}
                    onClick={() => openDelete(p)}
                  >
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
                      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                      aria-hidden="true">
                      <path d="M3 6h18" />
                      <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                      <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                      <path d="M10 11v6M14 11v6" />
                    </svg>
                  </button>
                </div>
              </div>
            ))
          )}

          {/* Footer bar */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '24px',
            padding: '0 20px',
            height: '34px',
            borderTop: '1px solid var(--border-default)',
            background: 'var(--bg-elevated)',
          }}>
            <span style={{
              fontSize: '10px',
              color: 'var(--text-muted)',
              fontFamily: 'ui-monospace, monospace',
              letterSpacing: '0.05em',
            }}>ENCRYPTED SESSION</span>
            <span style={{
              fontSize: '10px',
              color: 'var(--text-muted)',
              fontFamily: 'ui-monospace, monospace',
              letterSpacing: '0.05em',
            }}>DB: LEDGER-MAIN-01</span>
          </div>
        </div>
      </main>

      {target && (
        <ConfirmDialog
          title="Delete project?"
          confirmLabel="Delete permanently"
          danger
          busy={deleting}
          error={deleteError}
          onConfirm={confirmDelete}
          onCancel={closeDelete}
          body={
            <>
              <p style={{ margin: 0 }}>
                Project{' '}
                <strong style={{ color: 'var(--text-primary)', fontFamily: 'ui-monospace, monospace' }}>
                  {target.project_name}
                </strong>{' '}
                and all associated data will be <strong>permanently</strong> deleted.
              </p>
              {preview ? (
                <ul style={{ margin: '12px 0 0', paddingLeft: '18px' }}>
                  <li>{preview.scans} scans &middot; {preview.signals} signals &middot; {preview.docs} documents</li>
                  <li>{preview.vault_secrets} vault secret(s) &middot; {preview.files} file(s) on disk</li>
                </ul>
              ) : previewError ? (
                <p style={{ margin: '12px 0 0', color: 'var(--state-warn)' }}>{previewError}</p>
              ) : (
                <p style={{ margin: '12px 0 0', color: 'var(--text-muted)' }}>Loading preview&hellip;</p>
              )}
              <p style={{ margin: '12px 0 0', fontSize: '12px', color: 'var(--text-muted)' }}>
                This cannot be undone.
              </p>
            </>
          }
        />
      )}
    </div>
  )
}
