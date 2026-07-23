'use client'
import { Suspense, useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { getMeasures, saveMeasure, rerenderRun, type MeasuresResponse } from '../../../lib/api'
import Sidebar from '../../../components/Sidebar'

// ADR-127 PR5d Teil 3 + PR5e-5 — owner measures editor incl. owner-authored
// custom measures (add / title edit / immediate delete with confirm).
// Mirrors the /docs page styling (CSS vars + JetBrains Mono accents, dark theme).
// ADR-129 B-1 (language-pure owner texts): DE/EN view toggle. Writes go to the
// ACTIVE language only — never a mirror/copy into the other language's row.
// A control with owner text in the other language shows an empty field plus the
// other-language text read-only as a translation template.

type Lang = 'de' | 'en'
const mono = { fontFamily: "'JetBrains Mono', monospace" } as const

type LocalState = { text: string | null; title: string; deleted: boolean }

interface RowState {
  control_id: string
  framework: string
  isCustom: boolean
  default_text: string
  // owner text of the OTHER language (translation template; read-only display)
  templateText: string
  initial: LocalState
  local: LocalState
}

function deriveRows(data: MeasuresResponse, lang: Lang): RowState[] {
  const other: Lang = lang === 'de' ? 'en' : 'de'
  return Object.keys(data.measures)
    .sort()
    .map(cid => {
      const e = data.measures[cid]
      const active = e[lang]
      const sibling = e[other]
      const init: LocalState = {
        text: active?.text ?? null,
        // title falls back to the other lang: the row must stay identifiable
        // in a language whose row does not exist yet (rule 4: title appears).
        title: active?.title ?? sibling?.title ?? '',
        deleted: e.deleted,
      }
      return {
        control_id: cid,
        framework: active?.framework ?? sibling?.framework ?? '',
        isCustom: cid.startsWith('custom-'),
        default_text: active?.default_text ?? '',
        templateText: sibling?.text ?? '',
        initial: init,
        local: { ...init },
      }
    })
    // rows without any identity in either lang (defensive; shouldn't happen)
    .filter(r => r.initial.title !== '' || r.default_text !== '')
}

function StateBadge({ deleted, edited }: { deleted: boolean; edited: boolean }) {
  const [glyph, label, color] = deleted
    ? ['⊘', 'deaktiviert', 'var(--text-muted)']
    : edited
      ? ['✓', 'confirmed', '#4ade80']
      : ['☐', 'to confirm', 'var(--text-secondary)']
  return (
    <span style={{ ...mono, fontSize: '11px', color, flexShrink: 0 }}>
      {glyph} {label}
    </span>
  )
}

const ghostBtn = (busy: boolean) => ({
  ...mono, fontSize: '11px', padding: '3px 10px', borderRadius: '4px',
  background: 'transparent', border: '1px solid var(--border-default)',
  color: 'var(--text-muted)', cursor: busy ? 'not-allowed' : 'pointer',
}) as const

function MeasuresContent() {
  const searchParams = useSearchParams()
  const runId = searchParams.get('run') || ''

  const [lang, setLang] = useState<Lang>('de')
  const [rows, setRows] = useState<RowState[]>([])
  const [projectName, setProjectName] = useState('')
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [phase, setPhase] = useState<'idle' | 'saving' | 'rendering'>('idle')
  const [saveError, setSaveError] = useState<string | null>(null)
  const [done, setDone] = useState(false)
  // PR5e-5: add-measure inline form
  const [showAdd, setShowAdd] = useState(false)
  const [newTitle, setNewTitle] = useState('')
  const [newText, setNewText] = useState('')

  const reload = (l: Lang = lang) =>
    getMeasures(runId).then(d => { setRows(deriveRows(d, l)); setProjectName(d.project_name) })

  useEffect(() => {
    if (!runId) { setLoadError('Kein Scan angegeben (?run=… fehlt).'); setLoading(false); return }
    getMeasures(runId)
      .then(d => { setRows(deriveRows(d, 'de')); setProjectName(d.project_name); setLoading(false) })
      .catch(() => { setLoadError('No editable scan for this ID (or load error).'); setLoading(false) })
  }, [runId])

  // ADR-129 B-1: language toggle re-derives rows from a fresh load. Unsaved
  // edits belong to the previous view's language — never carry them over.
  const switchLang = async (next: Lang) => {
    if (next === lang || phase !== 'idle') return
    if (rows.some(isDirty) &&
        !window.confirm('Discard unsaved changes? (Switching language reloads)')) return
    setSaveError(null)
    setDone(false)
    setLang(next)
    try { await reload(next) } catch { setSaveError('Reload failed.') }
  }

  const setLocal = (cid: string, patch: Partial<LocalState>) => {
    setRows(rs => rs.map(r => r.control_id === cid ? { ...r, local: { ...r.local, ...patch } } : r))
    setDone(false)
  }

  const isDirty = (r: RowState) =>
    r.local.text !== r.initial.text || r.local.title !== r.initial.title || r.local.deleted !== r.initial.deleted
  const dirtyRows = rows.filter(isDirty)

  const handleSave = async () => {
    setSaveError(null)
    setPhase('saving')
    try {
      // 1) persist each dirty row's changes (collected, in order).
      // ADR-129 B-1: every write carries the ACTIVE view language — the other
      // language's row is never touched (language-pure owner texts).
      for (const r of dirtyRows) {
        if (r.local.deleted !== r.initial.deleted) {
          await saveMeasure(runId, r.control_id, lang, r.local.deleted ? 'deactivate' : 'reactivate')
        }
        if (r.isCustom) {
          // custom rows: never reset; title rides along with the edit
          if (r.local.text !== r.initial.text || r.local.title !== r.initial.title) {
            await saveMeasure(runId, r.control_id, lang, 'edit',
              r.local.text ?? r.initial.text ?? '', r.local.title)
          }
        } else if (r.local.text !== r.initial.text) {
          if (r.local.text != null) {
            await saveMeasure(runId, r.control_id, lang, 'edit', r.local.text)
          } else {
            await saveMeasure(runId, r.control_id, lang, 'reset')
          }
        }
      }
      // 2) one re-render of exactly this run (P4.6, synchronous — overwrites in place)
      setPhase('rendering')
      await rerenderRun(runId)
      // 3) commit local → initial, clear dirty
      setRows(rs => rs.map(r => ({ ...r, initial: { ...r.local } })))
      setDone(true)
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : String(e))
    } finally {
      setPhase('idle')
    }
  }

  // PR5e-5: immediate delete with confirm — custom rows only, no batching.
  // Docs update on the next "Save & re-render" (single render trigger).
  const handleDelete = async (cid: string) => {
    if (!window.confirm('Delete this measure permanently? It will not come back after a re-scan.')) return
    setSaveError(null)
    setPhase('saving')
    try {
      await saveMeasure(runId, cid, lang, 'delete')
      setRows(rs => rs.filter(r => r.control_id !== cid))
      setDone(false)
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : String(e))
    } finally {
      setPhase('idle')
    }
  }

  // PR5e-5: create a custom measure — server generates the id; reload picks it up.
  const handleAdd = async () => {
    if (!newTitle.trim() || !newText.trim()) { setSaveError('Title and text are required.'); return }
    // B-7 dirty guard (same pattern as switchLang): reload() below replaces all
    // rows, so unsaved edits would be lost — never silently. Cancel keeps both
    // the edits and the add form's input.
    if (rows.some(isDirty) &&
        !window.confirm('Discard unsaved changes? (Adding reloads)')) return
    setSaveError(null)
    setPhase('saving')
    try {
      // add creates the custom in the ACTIVE language (rule 3) — the other
      // language shows it as translation-pending until the owner writes it.
      await saveMeasure(runId, null, lang, 'add', newText.trim(), newTitle.trim())
      await reload()
      setShowAdd(false); setNewTitle(''); setNewText('')
      setDone(false)
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : String(e))
    } finally {
      setPhase('idle')
    }
  }

  const busy = phase !== 'idle'

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-base)', display: 'flex' }}>
      <Sidebar />
      <main style={{ flex: 1, padding: '40px 56px', minWidth: 0, paddingBottom: '96px' }}>
        <Link href="/docs" style={{ ...mono, fontSize: '12px', color: 'var(--text-muted)', textDecoration: 'none' }}>
          ← Compliance Docs
        </Link>

        <h1 style={{ fontSize: '28px', fontWeight: 700, color: 'var(--text-primary)', margin: '12px 0 4px', letterSpacing: '-0.02em' }}>
          Edit measures
        </h1>
        <p style={{ ...mono, fontSize: '12px', color: 'var(--text-muted)', margin: '0 0 8px' }}>
          {projectName ? `${projectName} · ` : ''}Run {runId.slice(0, 8)}
        </p>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: '0 0 16px', maxWidth: '760px', lineHeight: 1.5 }}>
          Measures from this scan. Adjust texts, confirm, deactivate — or add your own measures.
        </p>

        {/* ADR-129 B-1: language view toggle — texts are language-pure, the
            deactivate-state is shared (deleted_controls is lang-agnostic). */}
        <div style={{ display: 'flex', gap: '0', marginBottom: '24px' }}>
          {(['de', 'en'] as Lang[]).map(l => (
            <button
              key={l}
              onClick={() => switchLang(l)}
              disabled={busy}
              style={{
                ...mono, fontSize: '11px', padding: '4px 14px', cursor: busy ? 'not-allowed' : 'pointer',
                background: lang === l ? 'rgba(74,143,255,0.08)' : 'transparent',
                border: `1px solid ${lang === l ? 'var(--accent)' : 'var(--border-default)'}`,
                borderRadius: l === 'de' ? '4px 0 0 4px' : '0 4px 4px 0',
                color: lang === l ? 'var(--accent)' : 'var(--text-muted)',
              }}
            >
              {l.toUpperCase()}
            </button>
          ))}
          <span style={{ ...mono, fontSize: '11px', color: 'var(--text-muted)', alignSelf: 'center', marginLeft: '12px' }}>
            {lang === 'de' ? 'German measure texts' : 'English measure texts'}
          </span>
        </div>

        {loading && <div style={{ ...mono, fontSize: '13px', color: 'var(--text-muted)', padding: '48px 0' }}>Loading measures…</div>}

        {loadError && (
          <div style={{ ...mono, fontSize: '13px', color: 'var(--text-secondary)', padding: '32px 0' }}>
            {loadError} <Link href="/docs" style={{ color: 'var(--accent)' }}>→ back to documents</Link>
          </div>
        )}

        {!loading && !loadError && rows.map(r => {
          // ADR-129 B-1: a custom without text in the ACTIVE language is pending,
          // not confirmed — its text lives in the other language only.
          const edited = r.isCustom ? (r.local.text ?? '') !== '' : r.local.text != null
          const value = r.local.text ?? r.default_text
          return (
            <div key={r.control_id} style={{
              background: 'var(--bg-surface)', border: '1px solid var(--border-default)',
              borderRadius: '6px', padding: '14px 16px', marginBottom: '12px',
              opacity: r.local.deleted ? 0.55 : 1,
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '10px' }}>
                <span style={{ ...mono, fontSize: '12px', color: 'var(--text-primary)', fontWeight: 600 }}>
                  {r.control_id}
                </span>
                {r.isCustom ? (
                  <input
                    value={r.local.title}
                    maxLength={200}
                    disabled={r.local.deleted || busy}
                    onChange={e => setLocal(r.control_id, { title: e.target.value })}
                    style={{
                      flex: 1, minWidth: 0, fontSize: '13px', color: 'var(--text-primary)',
                      background: 'var(--bg-base)', border: '1px solid var(--border-default)',
                      borderRadius: '4px', padding: '4px 8px', fontFamily: 'inherit',
                    }}
                  />
                ) : (
                  <span style={{ flex: 1, fontSize: '13px', color: 'var(--text-secondary)', minWidth: 0 }}>
                    {r.initial.title} <span style={{ ...mono, fontSize: '11px', color: 'var(--text-muted)' }}>({r.framework})</span>
                  </span>
                )}
                <StateBadge deleted={r.local.deleted} edited={edited} />
              </div>

              <textarea
                value={value}
                disabled={r.local.deleted || busy}
                onChange={e => setLocal(r.control_id, { text: e.target.value })}
                rows={3}
                maxLength={2000}
                placeholder={r.templateText
                  ? (lang === 'de'
                      ? 'Enter the measure in German — English version below'
                      : 'Enter the measure in English — German version below')
                  : undefined}
                style={{
                  width: '100%', boxSizing: 'border-box', resize: 'vertical',
                  background: 'var(--bg-base)', color: 'var(--text-primary)',
                  border: '1px solid var(--border-default)', borderRadius: '4px',
                  padding: '8px 10px', fontSize: '13px', lineHeight: 1.5,
                  fontFamily: 'inherit',
                }}
              />

              {/* ADR-129 B-1: other-language owner text as read-only translation
                  template — displayed only, never written into this language. */}
              {r.templateText && !r.local.deleted && !(r.local.text ?? '') && (
                <div style={{
                  marginTop: '6px', padding: '8px 10px', borderRadius: '4px',
                  background: 'var(--bg-base)', border: '1px dashed var(--border-default)',
                }}>
                  <div style={{ ...mono, fontSize: '10px', color: 'var(--text-muted)', marginBottom: '4px' }}>
                    {lang === 'de' ? 'Englische Fassung (Übersetzungsvorlage, nur Ansicht)' : 'Deutsche Fassung (Übersetzungsvorlage, nur Ansicht)'}
                  </div>
                  <div style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.5, whiteSpace: 'pre-wrap' }}>
                    {r.templateText}
                  </div>
                </div>
              )}

              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '8px' }}>
                <button
                  onClick={() => setLocal(r.control_id, { deleted: !r.local.deleted })}
                  disabled={busy}
                  style={ghostBtn(busy)}
                >
                  {r.local.deleted ? '↺ wieder aktivieren' : '⊘ deaktivieren'}
                </button>
                {edited && !r.local.deleted && !r.isCustom && (
                  <button
                    onClick={() => setLocal(r.control_id, { text: null })}
                    disabled={busy}
                    style={ghostBtn(busy)}
                  >
                    ⟳ reset to default
                  </button>
                )}
                {r.isCustom && (
                  <button
                    onClick={() => handleDelete(r.control_id)}
                    disabled={busy}
                    style={{ ...ghostBtn(busy), color: '#f87171' }}
                  >
                    🗑 delete
                  </button>
                )}
              </div>
            </div>
          )
        })}

        {/* PR5e-5: add a custom measure (title + text, both required) */}
        {!loading && !loadError && (
          <div style={{ marginTop: '4px', marginBottom: '24px' }}>
            {!showAdd ? (
              <button onClick={() => setShowAdd(true)} disabled={busy} style={ghostBtn(busy)}>
                + Add measure
              </button>
            ) : (
              <div style={{
                background: 'var(--bg-surface)', border: '1px solid var(--border-default)',
                borderRadius: '6px', padding: '14px 16px',
              }}>
                <input
                  value={newTitle}
                  maxLength={200}
                  placeholder="Measure title (required)"
                  disabled={busy}
                  onChange={e => setNewTitle(e.target.value)}
                  style={{
                    width: '100%', boxSizing: 'border-box', fontSize: '13px',
                    color: 'var(--text-primary)', background: 'var(--bg-base)',
                    border: '1px solid var(--border-default)', borderRadius: '4px',
                    padding: '6px 10px', fontFamily: 'inherit', marginBottom: '8px',
                  }}
                />
                <textarea
                  value={newText}
                  maxLength={2000}
                  placeholder="Concrete implementation (required)"
                  disabled={busy}
                  onChange={e => setNewText(e.target.value)}
                  rows={3}
                  style={{
                    width: '100%', boxSizing: 'border-box', resize: 'vertical',
                    background: 'var(--bg-base)', color: 'var(--text-primary)',
                    border: '1px solid var(--border-default)', borderRadius: '4px',
                    padding: '8px 10px', fontSize: '13px', lineHeight: 1.5,
                    fontFamily: 'inherit', marginBottom: '8px',
                  }}
                />
                <div style={{ display: 'flex', gap: '12px' }}>
                  <button
                    onClick={handleAdd}
                    disabled={busy || !newTitle.trim() || !newText.trim()}
                    style={{ ...ghostBtn(busy), color: 'var(--accent)', borderColor: 'var(--accent)' }}
                  >
                    Anlegen
                  </button>
                  <button
                    onClick={() => { setShowAdd(false); setNewTitle(''); setNewText('') }}
                    disabled={busy}
                    style={ghostBtn(busy)}
                  >
                    Abbrechen
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </main>

      {/* Sticky save bar (SaveBar pattern) */}
      {!loading && !loadError && (
        <div style={{
          position: 'fixed', bottom: 0, left: 0, right: 0,
          background: 'var(--bg-surface)', borderTop: '1px solid var(--border-default)',
          padding: '12px 56px', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          marginLeft: '260px',  // clear the sidebar (Sidebar width)
        }}>
          <div style={{ ...mono, fontSize: '12px', color: 'var(--text-muted)' }}>
            {saveError ? <span style={{ color: '#f87171' }}>{saveError}</span>
              : done ? <span style={{ color: '#4ade80' }}>Saved + re-rendered · <Link href="/docs" style={{ color: 'var(--accent)' }}>→ documents</Link></span>
              : `${dirtyRows.length} change(s) · not saved automatically`}
          </div>
          <button
            onClick={handleSave}
            disabled={busy || dirtyRows.length === 0}
            style={{
              ...mono, fontSize: '12px', padding: '8px 16px', borderRadius: '4px',
              background: (busy || dirtyRows.length === 0) ? 'transparent' : 'rgba(74,143,255,0.08)',
              border: `1px solid ${(busy || dirtyRows.length === 0) ? 'var(--border-default)' : 'var(--accent)'}`,
              color: (busy || dirtyRows.length === 0) ? 'var(--text-muted)' : 'var(--accent)',
              cursor: (busy || dirtyRows.length === 0) ? 'not-allowed' : 'pointer',
            }}
          >
            {phase === 'saving' ? 'Saving…' : phase === 'rendering' ? 'Rendering…' : 'Save & re-render →'}
          </button>
        </div>
      )}
    </div>
  )
}

export default function MeasuresPage() {
  return (
    <Suspense fallback={<div style={{ minHeight: '100vh', background: 'var(--bg-base)' }} />}>
      <MeasuresContent />
    </Suspense>
  )
}
