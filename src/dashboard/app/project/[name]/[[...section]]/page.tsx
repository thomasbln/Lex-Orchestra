'use client'
// ADR-081: Project Workspace — /project/[name]/[section]
//
// Six independent sections, each with its own save action:
//   repos        → project_repos (POST /config/project-repos)
//   company      → project_config + project_setups DPO (two parallel POSTs)
//   hosting      → project_setups (merged with current state)
//   retention    → project_setups (merged with current state)
//   integrations → project_integrations via vault (per-integration actions)
//   scans        → read-only + "Run scan" button
//
// Data is loaded once on mount and distributed to sections.
// Middleware redirects /settings?project=X → /project/X/company.

import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import { useCallback, useEffect, useState } from 'react'
import Sidebar from '../../../../components/Sidebar'
import { useReadiness } from '../../../../components/useReadiness'
import ProjectSidebar from '../../../../components/ProjectSidebar'
import SecretInput from '../../../../components/SecretInput'
import { Inspector } from '../../../../components/Inspector'
import { InspectorProvider } from '../../../../contexts/InspectorContext'
import {
  getProjectConfig,
  getProjectSetup,
  getProjectRepos,
  getScanSignalsSummary,
  getIntegrationCatalog,
  getProjectIntegrations,
  saveProjectCompany,
  saveProjectSetup,
  saveProjectRepos,
  saveInstructingPersons,
  saveProjectAi,
  getAiServices,
  getUseCases,
  getAiProviders,
  upsertProjectIntegration,
  deleteProjectIntegration,
  triggerScan,
  extractImpressum,
  type ProjectSetupPayload,
  type RetentionPolicyIn,
  type CatalogIntegration,
  type ProjectIntegration,
  type RepoEntry,
  type ScanSignalsSummary,
  type AiConfig,
  type AiServiceFields,
  type UseCaseOption,
} from '../../../../lib/api'

// ── Shared style tokens ─────────────────────────────────────────────────────

const inputClass =
  'w-full bg-[#0a0d14] border border-[#1e2640] rounded px-4 py-2.5 text-sm ' +
  'text-white placeholder-[#4a5568] outline-none transition-all cursor-text ' +
  'focus:shadow-[0_0_0_1px_#4a8fff,0_0_8px_rgba(74,143,255,0.15)]'

const btnPrimary =
  'bg-[#4a8fff] disabled:bg-[#1e2640] text-white disabled:text-[#4a5568] ' +
  'px-6 py-2 rounded-sm text-sm tracking-wider transition-all cursor-pointer ' +
  'disabled:cursor-not-allowed'

const btnSecondary =
  'bg-transparent border border-[#1e2640] text-[#94a3b8] hover:text-white ' +
  'hover:border-[#4a5568] px-4 py-2 rounded-sm text-sm transition-all cursor-pointer'

const btnDanger =
  'bg-transparent border border-[#f87171]/30 text-[#f87171] hover:border-[#f87171]/60 ' +
  'px-4 py-2 rounded-sm text-sm transition-all cursor-pointer'

const HOSTING_PROVIDERS = [
  'AWS', 'GCP', 'Azure', 'Hetzner', 'IONOS', 'OVH', 'Strato',
  'Supabase Cloud', 'Vercel', 'Railway', 'Fly.io', 'Cloudflare',
]

// 'integrations' unmounted for v1.0 (verdict 2026-07-19, row 57j): every
// catalog card took secrets without a consumer. Section code stays below
// for the graph-fed return; project_integrations on live systems is empty
// and the disconnect route purges vault secrets correctly.
const VALID_SECTIONS = ['repos', 'company', 'hosting', 'retention', 'scans', 'instructing_persons', 'ai'] as const
type Section = typeof VALID_SECTIONS[number]

// ── Page-level state types ──────────────────────────────────────────────────

type InstructingPersonsEntry = { name: string; title: string }

type ConfigData = {
  company_name: string
  doc_language: 'de' | 'en'
  legal_form: string
  address: string
  zip_code: string
  city: string
  contact_email: string
  website_url: string
  responsible_name: string
  responsible_title: string
  register_court: string
  register_number: string
  dpo_name: string
  dpo_email: string
  instructing_persons: InstructingPersonsEntry[]
  ai_config: AiConfig
}

type SetupData = {
  on_prem: boolean
  hosting_provider: string
  hosting_region: string
}

type RepoRow = {
  repo_url: string
  label: string
  is_primary: boolean
  token_configured: boolean
}

// ── Main page ───────────────────────────────────────────────────────────────

export default function ProjectWorkspace() {
  const params = useParams()
  const router = useRouter()

  const name = decodeURIComponent(params.name as string)
  const sectionParam = params.section
  const rawSection = Array.isArray(sectionParam) ? sectionParam[0] : sectionParam
  const section: Section =
    VALID_SECTIONS.includes(rawSection as Section) ? (rawSection as Section) : 'repos'

  // ── Loaded state ────────────────────────────────────────────────────────
  const [loading, setLoading] = useState(true)
  const [config, setConfig] = useState<ConfigData | null>(null)
  const [setup, setSetup] = useState<SetupData | null>(null)
  const [retentionPolicies, setRetentionPolicies] = useState<RetentionPolicyIn[]>([])
  const [repos, setRepos] = useState<RepoRow[]>([])
  const [signalsSummary, setSignalsSummary] = useState<ScanSignalsSummary | null>(null)

  useEffect(() => {
    if (!name) return
    Promise.all([
      getProjectConfig(name),
      getProjectSetup(name),
      getProjectRepos(name),
      getScanSignalsSummary(name),
    ]).then(([cfg, setupRes, reposRes, signals]) => {
      const s = setupRes.setup

      setConfig({
        company_name:      cfg?.company_name ?? '',
        doc_language:      (cfg?.doc_language === 'en' ? 'en' : 'de'),
        legal_form:        cfg?.legal_form ?? '',
        address:           cfg?.address ?? '',
        zip_code:          cfg?.zip_code ?? '',
        city:              cfg?.city ?? '',
        contact_email:     cfg?.contact_email ?? '',
        website_url:       cfg?.website_url ?? '',
        responsible_name:  cfg?.responsible_name ?? '',
        responsible_title: cfg?.responsible_title ?? '',
        register_court:    cfg?.register_court ?? '',
        register_number:   cfg?.register_number ?? '',
        dpo_name:          cfg?.dpo_name  ?? '',
        dpo_email:         cfg?.dpo_email ?? '',
        instructing_persons:   Array.isArray(cfg?.instructing_persons) ? cfg.instructing_persons : [],
        ai_config:         (cfg?.ai_config && typeof cfg.ai_config === 'object')
                             ? { project_level: cfg.ai_config.project_level ?? {}, per_service: cfg.ai_config.per_service ?? {} }
                             : { project_level: {}, per_service: {} },
      })

      setSetup({
        on_prem:          s?.on_prem ?? false,
        hosting_provider: s?.hosting_provider ?? '',
        hosting_region:   s?.hosting_region ?? '',
      })

      setRetentionPolicies(
        (setupRes.retention_policies || [])
          .filter((r: RetentionPolicyIn) => r.source === 'setup')
          .map((r: RetentionPolicyIn) => ({
            category:     r.category,
            duration_days: r.duration_days,
            duration_raw:  r.duration_raw,
            source:        'setup' as const,
          }))
      )

      setRepos((reposRes.repos || []) as RepoRow[])
      setSignalsSummary(signals)
    }).finally(() => setLoading(false))
  }, [name])

  // ── Render ──────────────────────────────────────────────────────────────

  const SECTION_TITLES: Record<Section, string> = {
    repos:             'Repositories',
    company:           'Company & DPO',
    hosting:           'Hosting',
    retention:         'Retention Policies',
    scans:             'Scans',
    instructing_persons:   'Instructing persons (AVV)',
    ai:                'AI details (EU AI Act)',
  }

  return (
    <InspectorProvider projectName={name}>
    <div style={{ minHeight: '100vh', background: 'var(--bg-base)', display: 'flex' }}>
      <Sidebar />
      <ProjectSidebar projectName={name} activeSection={section} />

      <main style={{ flex: 1, minWidth: 0 }}>
        {/* Header */}
        <div style={{
          padding: '32px 48px 20px',
          borderBottom: '1px solid var(--border-default)',
        }}>
          <h1 style={{
            fontSize: '22px', fontWeight: 700,
            color: 'var(--text-primary)',
            margin: '0 0 4px', letterSpacing: '-0.01em',
          }}>
            {SECTION_TITLES[section]}
          </h1>
          <p style={{
            fontSize: '12px', color: 'var(--text-muted)',
            fontFamily: 'ui-monospace, monospace', margin: 0,
          }}>
            {name}
          </p>
        </div>

        <div style={{ padding: '32px 48px' }}>
          {loading ? (
            <div style={{ fontSize: '13px', color: 'var(--text-muted)', fontFamily: 'ui-monospace, monospace' }}>
              Loading…
            </div>
          ) : (
            <>
              {section === 'repos' && (
                <ReposSection
                  projectName={name}
                  initialRepos={repos}
                  onReposSaved={setRepos}
                  docLanguage={config ? config.doc_language : null}
                />
              )}
              {section === 'company' && config && (
                <CompanySection
                  projectName={name}
                  initialConfig={config}
                  onSaved={setConfig}
                />
              )}
              {section === 'hosting' && setup && (
                <HostingSection
                  projectName={name}
                  initialSetup={setup}
                  retentionPolicies={retentionPolicies}
                  onSaved={setSetup}
                />
              )}
              {section === 'retention' && setup && (
                <RetentionSection
                  projectName={name}
                  currentSetup={setup}
                  initialPolicies={retentionPolicies}
                  onSaved={setRetentionPolicies}
                />
              )}
              {section === 'scans' && (
                <ScansSection
                  projectName={name}
                  signalsSummary={signalsSummary}
                  router={router}
                  docLanguage={config ? config.doc_language : null}
                />
              )}
              {section === 'instructing_persons' && config && (
                <InstructingPersonsSection
                  projectName={name}
                  initialEntries={config.instructing_persons}
                  onSaved={(entries) => setConfig(c => c ? { ...c, instructing_persons: entries } : c)}
                />
              )}
              {section === 'ai' && config && (
                <AISection
                  projectName={name}
                  initialAiConfig={config.ai_config}
                  onSaved={(ai) => setConfig(c => c ? { ...c, ai_config: ai } : c)}
                />
              )}
            </>
          )}
        </div>
      </main>
      <Inspector />
    </div>
    </InspectorProvider>
  )
}

// ── Section: Repositories ───────────────────────────────────────────────────

const API_BASE_CLIENT = typeof window !== 'undefined'
  ? `${window.location.protocol}//${window.location.hostname}:8001`
  : 'http://lex-agent:8001'

type RepoCheckState = 'unchecked' | 'checking' | 'ok' | 'private' | 'error'

type RepoFormRow = {
  repo_url: string
  is_primary: boolean
  token_configured: boolean  // existing vault secret
  new_token: string          // typed during this session
  check_state: RepoCheckState
  check_msg: string
}

function ReposSection({
  projectName,
  initialRepos,
  onReposSaved,
  docLanguage,
}: {
  projectName: string
  initialRepos: RepoRow[]
  onReposSaved: (r: RepoRow[]) => void
  docLanguage: 'de' | 'en' | null
}) {
  const toForm = (r: RepoRow): RepoFormRow => ({
    repo_url:         r.repo_url,
    is_primary:       r.is_primary,
    token_configured: r.token_configured,
    new_token:        '',
    check_state:      r.repo_url ? 'unchecked' : 'unchecked',
    check_msg:        '',
  })

  const [rows, setRows] = useState<RepoFormRow[]>(() =>
    initialRepos.length > 0
      ? initialRepos.map(toForm)
      : [{ repo_url: '', is_primary: true, token_configured: false, new_token: '', check_state: 'unchecked', check_msg: '' }]
  )
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  const updateUrl = (idx: number, url: string) => {
    setRows(p => {
      const next = [...p]
      next[idx] = { ...next[idx], repo_url: url, check_state: 'unchecked', check_msg: '', new_token: '' }
      return next
    })
  }

  const setPrimary = (idx: number) => {
    setRows(p => p.map((r, i) => ({ ...r, is_primary: i === idx })))
  }

  const addRepo = () => setRows(p => [
    ...p,
    { repo_url: '', is_primary: false, token_configured: false, new_token: '', check_state: 'unchecked', check_msg: '' },
  ])

  const removeRepo = (idx: number) => {
    setRows(p => {
      const next = p.filter((_, i) => i !== idx)
      if (next.length > 0 && !next.some(r => r.is_primary)) next[0] = { ...next[0], is_primary: true }
      return next
    })
  }

  const checkRepo = async (idx: number) => {
    const row = rows[idx]
    if (!row.repo_url.trim()) return
    setRows(p => { const n = [...p]; n[idx] = { ...n[idx], check_state: 'checking', check_msg: '' }; return n })
    try {
      const params = new URLSearchParams({ url: row.repo_url.trim() })
      if (row.new_token.trim()) params.set('token', row.new_token.trim())
      else if (row.token_configured) params.set('use_stored_token', '1')
      const res = await fetch(`${API_BASE_CLIENT}/utils/check-repo?${params}`)
      const data = await res.json()
      let state: RepoCheckState = 'error'
      let msg = data.message || ''
      if (data.status === 'accessible') { state = 'ok'; msg = '' }
      else if (data.status === 'private') { state = 'private'; msg = 'Private — enter an access token' }
      else if (data.status === 'invalid_token') { state = 'error'; msg = 'Invalid token' }
      setRows(p => { const n = [...p]; n[idx] = { ...n[idx], check_state: state, check_msg: msg }; return n })
    } catch {
      setRows(p => { const n = [...p]; n[idx] = { ...n[idx], check_state: 'error', check_msg: 'Network error — URL will be validated during scan' }; return n })
    }
  }

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    setSaved(false)
    const payload: RepoEntry[] = rows
      .filter(r => r.repo_url.trim())
      .map(r => ({
        repo_url:     r.repo_url.trim(),
        label:        'main',
        github_token: r.new_token.trim() || null,
        is_primary:   r.is_primary,
      }))
    try {
      await saveProjectRepos(projectName, payload)
      onReposSaved(rows.map(r => ({
        repo_url:         r.repo_url,
        label:            'main',
        is_primary:       r.is_primary,
        token_configured: r.token_configured || !!r.new_token.trim(),
      })))
      setRows(p => p.map(r => ({ ...r, new_token: '', token_configured: r.token_configured || !!r.new_token.trim() })))
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setSaving(false)
    }
  }

  const stateIcon: Record<RepoCheckState, string> = {
    unchecked: '',
    checking:  '…',
    ok:        '✓',
    private:   '🔒',
    error:     '✕',
  }
  const stateColor: Record<RepoCheckState, string> = {
    unchecked: 'var(--text-muted)',
    checking:  'var(--text-muted)',
    ok:        '#4ade80',
    private:   '#fbbf24',
    error:     '#f87171',
  }

  return (
    <div className="space-y-4 max-w-2xl">
      <SectionHint>
        Enter the repository URL. Click <strong>Check</strong> to verify access.
        If the repo is private, an access token field will appear.
        Tokens are stored encrypted in Supabase Vault — never in plaintext.
        {docLanguage && (
          <>
            <br />
            Documents: <strong>{docLanguage === 'en' ? 'English' : 'Deutsch'}</strong>{' · '}
            <Link href={`/project/${encodeURIComponent(projectName)}/company`} className="text-[#4a8fff] hover:underline">
              change →
            </Link>
          </>
        )}
      </SectionHint>

      {rows.map((row, idx) => (
        <div key={idx} style={{
          background: 'var(--bg-surface)',
          border: `1px solid ${row.check_state === 'ok' ? 'rgba(74,222,128,0.25)' : row.check_state === 'error' ? 'rgba(248,113,113,0.2)' : 'var(--border-default)'}`,
          borderRadius: '6px',
          padding: '16px',
        }}>
          {/* Header row */}
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <span className="text-xs text-[#94a3b8] uppercase tracking-wider font-medium">
                Repo {idx + 1}
              </span>
              {rows.length > 1 && (
                row.is_primary
                  ? <span className="text-xs text-[#4a8fff]">· primary</span>
                  : <button type="button" onClick={() => setPrimary(idx)}
                      className="text-xs text-[#475569] hover:text-[#94a3b8] cursor-pointer transition-colors">
                      set primary
                    </button>
              )}
            </div>
            <button type="button" onClick={() => removeRepo(idx)}
              className="text-[#f87171] hover:text-[#fca5a5] text-base w-5 h-5 flex items-center justify-center cursor-pointer"
              aria-label="Remove">×</button>
          </div>

          {/* URL + Check */}
          <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-start' }}>
            <div style={{ flex: 1 }}>
              <input
                value={row.repo_url}
                onChange={e => updateUrl(idx, e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') checkRepo(idx) }}
                placeholder="https://github.com/acme/myapp"
                className={inputClass}
              />
            </div>
            <button
              type="button"
              onClick={() => checkRepo(idx)}
              disabled={!row.repo_url.trim() || row.check_state === 'checking'}
              className={btnSecondary}
              style={{ flexShrink: 0, padding: '9px 14px', fontSize: '12px' }}
            >
              {row.check_state === 'checking' ? '…' : 'Check'}
            </button>
            {row.check_state !== 'unchecked' && (
              <span style={{
                fontSize: '16px',
                color: stateColor[row.check_state],
                flexShrink: 0,
                lineHeight: '38px',
              }}>
                {stateIcon[row.check_state]}
              </span>
            )}
          </div>

          {/* State message */}
          {row.check_msg && (
            <div style={{ fontSize: '11px', color: stateColor[row.check_state], marginTop: '6px', fontFamily: 'ui-monospace, monospace' }}>
              {row.check_msg}
            </div>
          )}

          {/* Token field — only for private/error or when token is already configured */}
          {(row.check_state === 'private' || row.check_state === 'error' || row.token_configured) && (
            <div className="mt-3">
              <Field label="Access token">
                <SecretInput
                  value={row.new_token}
                  onChange={v => setRows(p => { const n = [...p]; n[idx] = { ...n[idx], new_token: v, check_state: 'unchecked' }; return n })}
                  alreadyConfigured={row.token_configured}
                  placeholder="ghp_… / glpat-… / token"
                />
              </Field>
              {row.new_token.trim() && (
                <button type="button" onClick={() => checkRepo(idx)}
                  disabled={row.check_state === 'checking'}
                  className={`mt-2 ${btnSecondary} text-xs`}>
                  Verify with token
                </button>
              )}
            </div>
          )}
        </div>
      ))}

      <button type="button" onClick={addRepo} className={btnSecondary}>
        + Add repository
      </button>

      <SaveBar saving={saving} saved={saved} error={error} onSave={handleSave} label="SAVE REPOSITORIES" />
    </div>
  )
}

// ── Section: Company & DPO ──────────────────────────────────────────────────

function CompanySection({
  projectName,
  initialConfig,
  onSaved,
}: {
  projectName: string
  initialConfig: ConfigData
  onSaved: (c: ConfigData) => void
}) {
  const [form, setForm] = useState<ConfigData>(initialConfig)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [scanning, setScanning] = useState(false)
  const [scanMsg, setScanMsg] = useState<string | null>(null)

  const upd = <K extends keyof ConfigData>(k: K, v: ConfigData[K]) =>
    setForm(p => ({ ...p, [k]: v }))

  const handleWebsiteScan = async () => {
    if (!form.website_url) return
    setScanning(true)
    setScanMsg(null)
    try {
      const res = await extractImpressum(form.website_url)
      if (!res.success) {
        setScanMsg(res.error === 'not_configured' ? 'Firecrawl not configured' : 'No impressum found')
        return
      }
      const f = res.fields as Record<string, string>
      // Only fields the backend regex extraction can actually deliver —
      // register_court/register_number were dead map entries (never extracted).
      const FIELD_MAP: Array<[string, string]> = [
        ['company_name', 'company_name'],
        ['legal_form', 'legal_form'],
        ['address', 'address'],
        ['zip_code', 'zip_code'],
        ['city', 'city'],
        ['contact_email', 'contact_email'],
        ['responsible_name', 'responsible_name'],
      ]
      let filled = 0
      const patch: Record<string, string> = {}
      for (const [src, dst] of FIELD_MAP) {
        if (f[src]) { patch[dst] = f[src]; filled++ }
      }
      setForm(p => ({ ...p, ...patch }))
      setScanMsg(filled > 0 ? `${filled} field${filled > 1 ? 's' : ''} filled from impressum` : 'No fields extracted')
    } catch {
      setScanMsg('Scan failed')
    } finally {
      setScanning(false)
      setTimeout(() => setScanMsg(null), 5000)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    try {
      const res = await saveProjectCompany({
        project_name:      projectName,
        company_name:      form.company_name.trim() || null,
        legal_form:        form.legal_form.trim() || null,
        address:           form.address.trim() || null,
        zip_code:          form.zip_code.trim() || null,
        city:              form.city.trim() || null,
        contact_email:     form.contact_email.trim() || null,
        website_url:       form.website_url.trim() || null,
        responsible_name:  form.responsible_name.trim() || null,
        responsible_title: form.responsible_title.trim() || null,
        register_court:    form.register_court.trim() || null,
        register_number:   form.register_number.trim() || null,
        dpo_name:          form.dpo_name.trim() || null,
        dpo_email:         form.dpo_email.trim() || null,
        doc_language:      form.doc_language,
      })
      if (res?.detail) throw new Error(String(res.detail))
      onSaved(form)
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setSaving(false)
    }
  }

  const addressFilled = !!(form.address || form.zip_code || form.city)
  const legalFilled = !!(form.register_court || form.register_number)

  return (
    <div className="space-y-8 max-w-2xl">
      <Section title="Company">
        {/* Core — always visible */}
        <div className="grid grid-cols-2 gap-4">
          <Field label="Company name">
            <input value={form.company_name} onChange={e => upd('company_name', e.target.value)}
              placeholder="ACME GmbH" className={inputClass} />
          </Field>
          <Field label="Legal form">
            <input value={form.legal_form} onChange={e => upd('legal_form', e.target.value)}
              placeholder="GmbH" className={inputClass} />
          </Field>
        </div>
        {/* ADR-129 PR 13 (F2): document language — feeds the EN render chain */}
        <div className="grid grid-cols-2 gap-4">
          <Field label="Document language">
            <select value={form.doc_language}
              onChange={e => upd('doc_language', e.target.value === 'en' ? 'en' : 'de')}
              className={inputClass}>
              <option value="de">Deutsch</option>
              <option value="en">English</option>
            </select>
            <p className="mt-1 text-[11px] text-[#64748b]">
              Language of the generated legal documents — not the UI. Takes effect on the next scan or re-render.
            </p>
          </Field>
          <div />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Contact email">
            <input type="email" value={form.contact_email}
              onChange={e => upd('contact_email', e.target.value)}
              placeholder="hello@acme.test" className={inputClass} />
          </Field>
          <Field label="Website">
            <div className="flex gap-2">
              <input type="url" value={form.website_url}
                onChange={e => upd('website_url', e.target.value)}
                placeholder="https://acme.test" className={inputClass} />
              <button type="button" onClick={handleWebsiteScan}
                disabled={!form.website_url || scanning}
                className={`${btnSecondary} whitespace-nowrap text-xs disabled:opacity-40`}>
                {scanning ? 'Scanning…' : 'Scan →'}
              </button>
            </div>
            {scanMsg && (
              <p className="text-xs mt-1 text-[#94a3b8]">{scanMsg}</p>
            )}
            <p className="text-xs mt-1 text-[#475569]">
              Suggestions from your imprint via Firecrawl (cloud service) — please review before saving.
            </p>
          </Field>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Responsible person">
            <input value={form.responsible_name}
              onChange={e => upd('responsible_name', e.target.value)}
              placeholder="Max Muster" className={inputClass} />
          </Field>
          <Field label="Title">
            <input value={form.responsible_title}
              onChange={e => upd('responsible_title', e.target.value)}
              placeholder="CEO" className={inputClass} />
          </Field>
        </div>

        {/* Address — collapsible, open when empty */}
        <details open={!addressFilled} className="border-t border-[#1e2640] pt-4 mt-2">
          <summary className="text-xs text-[#4a5568] hover:text-[#94a3b8] cursor-pointer list-none transition-colors tracking-widest mb-3">
            ▸ ADDRESS {addressFilled && <span className="text-[#4a8fff] ml-2">✓ {form.city}</span>}
          </summary>
          <div className="space-y-4">
            <Field label="Street + number">
              <input value={form.address} onChange={e => upd('address', e.target.value)}
                placeholder="Example Street 1" className={inputClass} />
            </Field>
            <div className="grid grid-cols-2 gap-4">
              <Field label="ZIP">
                <input value={form.zip_code} onChange={e => upd('zip_code', e.target.value)}
                  placeholder="10115" className={inputClass} />
              </Field>
              <Field label="City">
                <input value={form.city} onChange={e => upd('city', e.target.value)}
                  placeholder="Berlin" className={inputClass} />
              </Field>
            </div>
          </div>
        </details>

        {/* Legal registration — collapsible, open when empty */}
        <details open={!legalFilled} className="border-t border-[#1e2640] pt-4 mt-2">
          <summary className="text-xs text-[#4a5568] hover:text-[#94a3b8] cursor-pointer list-none transition-colors tracking-widest mb-3">
            ▸ LEGAL REGISTRATION {legalFilled && <span className="text-[#4a8fff] ml-2">✓ {form.register_number}</span>}
          </summary>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Register court">
              <input value={form.register_court}
                onChange={e => upd('register_court', e.target.value)}
                placeholder="Amtsgericht Berlin" className={inputClass} />
            </Field>
            <Field label="Register number">
              <input value={form.register_number}
                onChange={e => upd('register_number', e.target.value)}
                placeholder="HRB 123456" className={inputClass} />
            </Field>
          </div>
        </details>
      </Section>

      <Section title="Data Protection Officer">
        <div className="grid grid-cols-2 gap-4">
          <Field label="Name">
            <input value={form.dpo_name} onChange={e => upd('dpo_name', e.target.value)}
              placeholder="Thomas Rehmer" className={inputClass} />
          </Field>
          <Field label="Email">
            <input type="email" value={form.dpo_email}
              onChange={e => upd('dpo_email', e.target.value)}
              placeholder="dpo@example.com" className={inputClass} />
          </Field>
        </div>
      </Section>

      <SaveBar saving={saving} saved={saved} error={error} onSave={handleSave} label="SAVE COMPANY" />
    </div>
  )
}

// ── Section: Hosting ────────────────────────────────────────────────────────

function HostingSection({
  projectName,
  initialSetup,
  retentionPolicies,
  onSaved,
}: {
  projectName: string
  initialSetup: SetupData
  retentionPolicies: RetentionPolicyIn[]
  onSaved: (s: SetupData) => void
}) {
  const [form, setForm] = useState<SetupData>(initialSetup)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const upd = <K extends keyof SetupData>(k: K, v: SetupData[K]) =>
    setForm(p => ({ ...p, [k]: v }))

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    try {
      const payload: ProjectSetupPayload = {
        on_prem:            form.on_prem,
        hosting_provider:   form.hosting_provider.trim() || null,
        hosting_region:     form.hosting_region.trim() || null,
        retention_policies: retentionPolicies.filter(r => r.category.trim() !== ''),
        created_by:         'dashboard',
      }
      const res = await saveProjectSetup(projectName, payload)
      if ('detail' in res) throw new Error(String(res.detail))
      onSaved(form)
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-8 max-w-3xl">
      <SectionHint>
        Determines the delegation block in TOM § 1.1 (physical access control).
      </SectionHint>
      <Section title="Infrastructure">
        <Toggle
          label="On-premise"
          description="We run our own data centre. Physical controls are handled internally."
          checked={form.on_prem}
          onChange={v => upd('on_prem', v)}
        />
        {!form.on_prem && (
          <>
            <Field label="Hosting provider">
              <select value={form.hosting_provider}
                onChange={e => upd('hosting_provider', e.target.value)}
                className={inputClass}>
                <option value="">— select provider —</option>
                {HOSTING_PROVIDERS.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
              <Hint>Curated list matches HostingProvider seed in Neo4j (ADR-076).</Hint>
            </Field>
            <Field label="Region">
              <input value={form.hosting_region}
                onChange={e => upd('hosting_region', e.target.value)}
                placeholder="eu-central-1" className={inputClass} />
            </Field>
          </>
        )}
      </Section>

      <SaveBar saving={saving} saved={saved} error={error} onSave={handleSave} label="SAVE HOSTING" />
    </div>
  )
}

// ── Section: Retention Policies ─────────────────────────────────────────────

const RETENTION_PRESETS = [
  { category: 'Server logs',         duration_raw: '7 days' },
  { category: 'User accounts',       duration_raw: 'Until account deletion' },
  { category: 'Purchase records',    duration_raw: '10 years (HGB § 257)' },
  { category: 'Support tickets',     duration_raw: '3 years' },
  { category: 'Email newsletter',    duration_raw: 'Until unsubscribe' },
]

function RetentionSection({
  projectName,
  currentSetup,
  initialPolicies,
  onSaved,
}: {
  projectName: string
  currentSetup: SetupData
  initialPolicies: RetentionPolicyIn[]
  onSaved: (p: RetentionPolicyIn[]) => void
}) {
  const [policies, setPolicies] = useState<RetentionPolicyIn[]>(initialPolicies)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const updatePolicy = (idx: number, key: 'category' | 'duration_raw', value: string) => {
    setPolicies(p => {
      const next = [...p]
      next[idx] = { ...next[idx], [key]: value }
      return next
    })
  }

  const addBlank = () => setPolicies(p => [
    ...p,
    { category: '', duration_days: null, duration_raw: '', source: 'setup' },
  ])

  const addPreset = (preset: typeof RETENTION_PRESETS[number]) => {
    const alreadyExists = policies.some(
      p => p.category.toLowerCase() === preset.category.toLowerCase()
    )
    if (alreadyExists) return
    setPolicies(p => [...p, { ...preset, duration_days: null, source: 'setup' }])
  }

  const removePolicy = (idx: number) => setPolicies(p => p.filter((_, i) => i !== idx))

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    try {
      const payload: ProjectSetupPayload = {
        on_prem:            currentSetup.on_prem,
        hosting_provider:   currentSetup.hosting_provider || null,
        hosting_region:     currentSetup.hosting_region || null,
        retention_policies: policies.filter(r => r.category.trim() !== ''),
        created_by:         'dashboard',
      }
      const res = await saveProjectSetup(projectName, payload)
      if ('detail' in res) throw new Error(String(res.detail))
      onSaved(policies)
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setSaving(false)
    }
  }

  const usedPresets = new Set(policies.map(p => p.category.toLowerCase()))

  return (
    <div className="space-y-6 max-w-3xl">

      {/* Explainer */}
      <div style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-default)',
        borderRadius: '4px',
        padding: '16px 18px',
        display: 'flex',
        flexDirection: 'column',
        gap: '6px',
      }}>
        <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', letterSpacing: '0.04em', textTransform: 'uppercase' }}>
          What are retention policies?
        </div>
        <div style={{ fontSize: '13px', color: 'var(--text-muted)', lineHeight: 1.6 }}>
          Your privacy policy must state how long you store each type of user data — and why.
          Lex-Orchestra puts these entries into your <span style={{ color: 'var(--text-secondary)', fontFamily: 'ui-monospace, monospace', fontSize: '12px' }}>privacy policy</span> and <span style={{ color: 'var(--text-secondary)', fontFamily: 'ui-monospace, monospace', fontSize: '12px' }}>VVT</span> automatically.
          The scanner detects many periods from your code — add the rest here manually.
        </div>
      </div>

      {/* Quick-add presets */}
      <div>
        <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '8px' }}>
          Common entries — click to add
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
          {RETENTION_PRESETS.map(preset => {
            const used = usedPresets.has(preset.category.toLowerCase())
            return (
              <button
                key={preset.category}
                type="button"
                onClick={() => addPreset(preset)}
                disabled={used}
                style={{
                  padding: '5px 10px',
                  fontSize: '11px',
                  fontFamily: 'ui-monospace, monospace',
                  borderRadius: '3px',
                  border: `1px solid ${used ? 'rgba(74,143,255,0.15)' : 'rgba(74,143,255,0.3)'}`,
                  background: used ? 'rgba(74,143,255,0.05)' : 'transparent',
                  color: used ? 'var(--text-muted)' : 'var(--accent)',
                  cursor: used ? 'default' : 'pointer',
                  transition: 'all 120ms ease',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                {used && <span style={{ opacity: 0.5 }}>✓</span>}
                {preset.category}
                <span style={{ opacity: 0.5 }}>·</span>
                {preset.duration_raw}
              </button>
            )
          })}
        </div>
      </div>

      {/* Table */}
      {policies.length > 0 && (
        <div>
          <div style={{
            display: 'grid',
            gridTemplateColumns: '2fr 2fr auto',
            gap: '8px',
            paddingBottom: '6px',
            marginBottom: '6px',
            borderBottom: '1px solid var(--border-default)',
          }}>
            <span style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Data category</span>
            <span style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Retention period</span>
            <span />
          </div>
          <div className="space-y-2">
            {policies.map((rp, idx) => (
              <div key={idx} style={{ display: 'grid', gridTemplateColumns: '2fr 2fr auto', gap: '8px', alignItems: 'center' }}>
                <input
                  value={rp.category}
                  onChange={e => updatePolicy(idx, 'category', e.target.value)}
                  placeholder="e.g. User accounts"
                  className={inputClass}
                />
                <input
                  value={rp.duration_raw}
                  onChange={e => updatePolicy(idx, 'duration_raw', e.target.value)}
                  placeholder="e.g. 7 days / Until deletion"
                  className={inputClass}
                />
                <button type="button" onClick={() => removePolicy(idx)}
                  style={{ color: '#f87171', fontSize: '16px', width: '28px', height: '36px', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', background: 'none', border: 'none' }}
                  aria-label="Remove">×</button>
              </div>
            ))}
          </div>
        </div>
      )}

      {policies.length === 0 && (
        <div style={{
          border: '1px dashed rgba(74,143,255,0.15)',
          borderRadius: '4px',
          padding: '20px 18px',
          fontSize: '12px',
          color: 'var(--text-muted)',
          fontFamily: 'ui-monospace, monospace',
          textAlign: 'center',
        }}>
          No entries yet — use the presets above or add a custom entry below.
        </div>
      )}

      <button type="button" onClick={addBlank} className={btnSecondary}>
        + Custom entry
      </button>

      <SaveBar saving={saving} saved={saved} error={error} onSave={handleSave} label="SAVE RETENTION" />
    </div>
  )
}

// ── Section: Integrations ───────────────────────────────────────────────────

function IntegrationsSection({
  projectName,
  catalog,
  initialIntegrations,
  onChanged,
}: {
  projectName: string
  catalog: CatalogIntegration[]
  initialIntegrations: ProjectIntegration[]
  onChanged: (i: ProjectIntegration[]) => void
}) {
  const [integrations, setIntegrations] = useState<ProjectIntegration[]>(initialIntegrations)
  const [busy, setBusy] = useState<Record<string, boolean>>({})
  const [keyInputs, setKeyInputs] = useState<Record<string, string>>({})
  const [errors, setErrors] = useState<Record<string, string>>({})

  const getProjectInt = (name: string) => integrations.find(i => i.integration === name)

  const connect = async (integration: string) => {
    setBusy(b => ({ ...b, [integration]: true }))
    setErrors(e => ({ ...e, [integration]: '' }))
    try {
      const apiKey = keyInputs[integration]?.trim() || undefined
      const res = await upsertProjectIntegration(projectName, integration, apiKey)
      if (!res.ok) throw new Error('Failed to connect')
      setIntegrations(prev => {
        const existing = prev.find(i => i.integration === integration)
        if (existing) {
          return prev.map(i => i.integration === integration
            ? { ...i, enabled: true, has_credentials: !!(apiKey || i.has_credentials), connected_at: new Date().toISOString() }
            : i
          )
        }
        return [...prev, {
          integration, enabled: true, has_credentials: !!apiKey,
          config: {}, connected_at: new Date().toISOString(),
          last_sync_at: null, last_error: null,
        }]
      })
      setKeyInputs(k => ({ ...k, [integration]: '' }))
    } catch (e) {
      setErrors(err => ({ ...err, [integration]: e instanceof Error ? e.message : String(e) }))
    } finally {
      setBusy(b => ({ ...b, [integration]: false }))
    }
  }

  const disconnect = async (integration: string) => {
    if (!confirm(`Disconnect ${integration}? The API key will be permanently deleted from the vault.`)) return
    setBusy(b => ({ ...b, [integration]: true }))
    try {
      await deleteProjectIntegration(projectName, integration)
      setIntegrations(prev => prev.filter(i => i.integration !== integration))
    } catch (e) {
      setErrors(err => ({ ...err, [integration]: e instanceof Error ? e.message : String(e) }))
    } finally {
      setBusy(b => ({ ...b, [integration]: false }))
    }
  }

  return (
    <div className="max-w-3xl space-y-4">
      <SectionHint>
        Integration catalog sourced from the Neo4j graph (ADR-082). API keys stored in Supabase Vault (ADR-083).
        Connecting an integration enables it for this project without affecting others.
      </SectionHint>

      {catalog.length === 0 && (
        <div className="text-xs text-[#4a5568]">
          No integrations in catalog — run <code className="text-[#4a8fff]">scripts/seed_both.py --module adr082</code>
        </div>
      )}

      {catalog.map(cat => {
        const proj = getProjectInt(cat.name)
        const connected = !!proj
        const hasKey = proj?.has_credentials ?? false
        const keyInput = keyInputs[cat.name] ?? ''
        const isbusy = busy[cat.name] ?? false

        return (
          <div key={cat.name} style={{
            background: 'var(--bg-surface)',
            border: `1px solid ${connected ? 'rgba(74,143,255,0.3)' : 'var(--border-default)'}`,
            borderRadius: '6px',
            padding: '16px 20px',
          }}>
            <div className="flex items-start justify-between gap-4 mb-3">
              <div>
                <div className="flex items-center gap-2">
                  <span style={{
                    fontSize: '14px', fontWeight: 600,
                    color: 'var(--text-primary)',
                    fontFamily: 'ui-monospace, monospace',
                  }}>{cat.name}</span>
                  {connected && (
                    <span style={{
                      fontSize: '10px', padding: '1px 6px',
                      background: 'rgba(74,143,255,0.15)',
                      color: '#4a8fff', borderRadius: '2px',
                      fontFamily: 'ui-monospace, monospace', letterSpacing: '0.05em',
                    }}>CONNECTED</span>
                  )}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '3px' }}>
                  {cat.subcategory} · {cat.pricing_tier}
                  {cat.region && ` · ${cat.region}`}
                  {cat.requires_scc && ' · SCC required'}
                </div>
              </div>
              {cat.documentation_url && (
                <a href={cat.documentation_url} target="_blank" rel="noreferrer"
                  style={{
                    fontSize: '11px', color: 'var(--text-muted)',
                    textDecoration: 'none', fontFamily: 'ui-monospace, monospace',
                    flexShrink: 0,
                  }}
                  onMouseEnter={e => { e.currentTarget.style.color = 'var(--accent)' }}
                  onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-muted)' }}
                >
                  docs ↗
                </a>
              )}
            </div>

            {cat.required_credentials.length > 0 && (
              <Field label={`API Key (${cat.required_credentials.join(', ')})`}>
                <SecretInput
                  value={keyInput}
                  onChange={v => setKeyInputs(k => ({ ...k, [cat.name]: v }))}
                  alreadyConfigured={hasKey}
                  placeholder="Enter API key…"
                  disabled={isbusy}
                />
              </Field>
            )}

            {errors[cat.name] && (
              <div className="text-xs text-[#f87171] mt-2">{errors[cat.name]}</div>
            )}

            <div className="flex gap-2 mt-3">
              <button
                type="button"
                onClick={() => connect(cat.name)}
                disabled={isbusy}
                className={btnPrimary}
              >
                {isbusy ? 'Saving…' : connected ? 'Update key' : 'Connect'}
              </button>
              {connected && (
                <button type="button" onClick={() => disconnect(cat.name)}
                  disabled={isbusy} className={btnDanger}>
                  Disconnect
                </button>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ── Section: Scans ──────────────────────────────────────────────────────────

function ScansSection({
  projectName,
  signalsSummary,
  router,
  docLanguage,
}: {
  projectName: string
  signalsSummary: ScanSignalsSummary | null
  router: ReturnType<typeof useRouter>
  docLanguage: 'de' | 'en' | null
}) {
  const [scanning, setScanning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // First-start gate (server enforces the same via 503 on POST /scan)
  const { readiness } = useReadiness()
  const preparing = readiness ? !readiness.ready : false

  const handleScan = async () => {
    setScanning(true)
    setError(null)
    try {
      const result = await triggerScan(projectName, 'manual')
      if (result.ok && result.scan_run_id) {
        const q = new URLSearchParams({ project: projectName, run: result.scan_run_id })
        router.push(`/scan?${q.toString()}`)
      } else {
        throw new Error(result.error || 'Scan could not be started — check backend logs')
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setScanning(false)
    }
  }

  const lastScan = signalsSummary?.last_scan_at
    ? new Date(signalsSummary.last_scan_at).toLocaleDateString('de-DE', {
        day: '2-digit', month: '2-digit', year: 'numeric',
        hour: '2-digit', minute: '2-digit',
      })
    : null

  return (
    <div className="max-w-2xl space-y-6">
      {/* Last scan summary */}
      <div style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-default)',
        borderRadius: '6px',
        padding: '20px 24px',
      }}>
        <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'ui-monospace, monospace', marginBottom: '8px', letterSpacing: '0.08em' }}>
          LAST SCAN
        </div>
        {lastScan ? (
          <>
            <div style={{ fontSize: '18px', fontWeight: 600, color: 'var(--text-primary)', fontFamily: 'ui-monospace, monospace' }}>
              {lastScan}
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px', fontFamily: 'ui-monospace, monospace' }}>
              {signalsSummary?.signals_count} signals detected
            </div>
          </>
        ) : (
          <div style={{ fontSize: '14px', color: 'var(--text-muted)' }}>No scans yet</div>
        )}
      </div>

      {/* Quick links */}
      <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
        <a href={`/logs?project=${encodeURIComponent(projectName)}`} style={{
          fontSize: '12px', color: 'var(--text-muted)',
          textDecoration: 'none', fontFamily: 'ui-monospace, monospace',
          padding: '6px 14px',
          border: '1px solid var(--border-default)',
          borderRadius: '4px',
          transition: 'all 150ms ease',
        }}
        onMouseEnter={e => { e.currentTarget.style.color = 'var(--text-primary)'; e.currentTarget.style.borderColor = '#4a8fff' }}
        onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-muted)'; e.currentTarget.style.borderColor = 'var(--border-default)' }}
        >
          View logs →
        </a>
        <a href={`/docs`} style={{
          fontSize: '12px', color: 'var(--text-muted)',
          textDecoration: 'none', fontFamily: 'ui-monospace, monospace',
          padding: '6px 14px',
          border: '1px solid var(--border-default)',
          borderRadius: '4px',
          transition: 'all 150ms ease',
        }}
        onMouseEnter={e => { e.currentTarget.style.color = 'var(--text-primary)'; e.currentTarget.style.borderColor = '#4a8fff' }}
        onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-muted)'; e.currentTarget.style.borderColor = 'var(--border-default)' }}
        >
          View documents →
        </a>
      </div>

      {/* Run scan */}
      <div style={{
        borderTop: '1px solid var(--border-default)',
        paddingTop: '24px',
      }}>
        <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '12px' }}>
          Triggers a full compliance scan using the current project configuration.
          You will be redirected to the live status page.
        </div>
        {docLanguage && (
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '12px' }}>
            Documents will be generated in:{' '}
            <strong style={{ color: 'var(--text-secondary)' }}>{docLanguage === 'en' ? 'English' : 'Deutsch'}</strong>{' · '}
            <Link href={`/project/${encodeURIComponent(projectName)}/company`} className="text-[#4a8fff] hover:underline">
              change →
            </Link>
          </div>
        )}
        {error && <div className="text-xs text-[#f87171] mb-3">{error}</div>}
        <button
          type="button"
          onClick={handleScan}
          disabled={scanning || preparing}
          title={preparing ? 'System preparing — see the status card on the dashboard' : undefined}
          className={btnPrimary}
        >
          {scanning ? 'STARTING SCAN…' : preparing ? 'SYSTEM PREPARING…' : 'RUN SCAN →'}
        </button>
      </div>
    </div>
  )
}

// ── Shared UI helpers ───────────────────────────────────────────────────────

function Section({ title, subtitle, children }: {
  title: string; subtitle?: string; children: React.ReactNode
}) {
  return (
    <section>
      <div className="border-b border-[#1e2640] pb-2 mb-4">
        <h2 className="text-white text-sm font-medium uppercase tracking-wider">{title}</h2>
        {subtitle && <p className="text-xs text-[#4a5568] mt-1">{subtitle}</p>}
      </div>
      <div className="space-y-4">{children}</div>
    </section>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs text-[#94a3b8] mb-1.5 uppercase tracking-wider">
        {label}
      </label>
      {children}
    </div>
  )
}

function Hint({ children }: { children: React.ReactNode }) {
  return <div className="text-xs text-[#475569] mt-1.5">{children}</div>
}

function SectionHint({ children }: { children: React.ReactNode }) {
  return (
    <div style={{
      background: 'rgba(74,143,255,0.06)',
      border: '1px solid rgba(74,143,255,0.15)',
      borderRadius: '4px',
      padding: '10px 14px',
      fontSize: '12px',
      color: 'rgba(148,163,184,0.8)',
    }}>
      {children}
    </div>
  )
}

function Toggle({ label, description, checked, onChange }: {
  label: string; description?: string; checked: boolean; onChange: (v: boolean) => void
}) {
  return (
    <button type="button" onClick={() => onChange(!checked)}
      className="w-full flex items-start gap-3 py-2 cursor-pointer text-left">
      <span className={`mt-0.5 inline-block w-4 h-4 rounded-sm border transition-all ${
        checked ? 'bg-[#4a8fff] border-[#4a8fff]' : 'bg-[#0a0d14] border-[#1e2640]'
      }`}>
        {checked && (
          <svg viewBox="0 0 16 16" className="w-4 h-4 text-white">
            <path d="M4 8l3 3 5-6" stroke="currentColor" strokeWidth="2"
              fill="none" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        )}
      </span>
      <div className="flex-1">
        <div className="text-sm text-[#e2e8f0]">{label}</div>
        {description && <div className="text-xs text-[#4a5568] mt-0.5">{description}</div>}
      </div>
    </button>
  )
}

function SaveBar({ saving, saved, error, onSave, label }: {
  saving: boolean
  saved: boolean
  error: string | null
  onSave: () => void
  label: string
}) {
  return (
    <div className="pt-4 border-t border-[#1e2640] flex items-center justify-between">
      <div className="text-xs text-[#4a5568]">
        {saved ? (
          <span className="text-[#4ade80]">Saved successfully</span>
        ) : (
          'Changes are not auto-saved.'
        )}
      </div>
      <div className="flex items-center gap-3">
        {error && (
          <span className="text-xs text-[#f87171] max-w-md truncate" title={error}>{error}</span>
        )}
        <button onClick={onSave} disabled={saving} className={btnPrimary}>
          {saving ? 'SAVING…' : `${label} →`}
        </button>
      </div>
    </div>
  )
}

function InstructingPersonsSection({
  projectName,
  initialEntries,
  onSaved,
}: {
  projectName: string
  initialEntries: InstructingPersonsEntry[]
  onSaved: (entries: InstructingPersonsEntry[]) => void
}) {
  const [entries, setEntries] = useState<InstructingPersonsEntry[]>(initialEntries)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const addEntry = () => setEntries(e => [...e, { name: '', title: '' }])
  const updateEntry = (idx: number, field: keyof InstructingPersonsEntry, value: string) =>
    setEntries(e => e.map((entry, i) => (i === idx ? { ...entry, [field]: value } : entry)))
  const removeEntry = (idx: number) =>
    setEntries(e => e.filter((_, i) => i !== idx))

  const handleSave = async () => {
    setSaving(true)
    setSaved(false)
    setError(null)
    const clean = entries.filter(e => e.name.trim())
    try {
      await saveInstructingPersons(projectName, clean)
      setEntries(clean)
      onSaved(clean)
      setSaved(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <Section title="Persons authorised to issue instructions">
        <p className="text-xs text-[#4a5568] mb-4">
          Under Art. 28(3)(a) GDPR, the processor may process only on documented instructions
          from the controller — the DPA (AVV) therefore names the persons authorised to issue them.
        </p>
        {entries.length === 0 && (
          <div className="text-xs text-[#f87171] mb-4 p-3 border border-[#f87171]/30 rounded bg-[#f87171]/5">
            No entries — the DPA is not signature-ready (GDPR Art. 28(3)(a))
          </div>
        )}
        <div className="space-y-3">
          {entries.map((entry, idx) => (
            <div key={idx} className="flex gap-3 items-start">
              <input
                type="text"
                placeholder="Name"
                value={entry.name}
                onChange={e => updateEntry(idx, 'name', e.target.value)}
                className="flex-1 bg-[#0d1117] border border-[rgba(255,255,255,0.07)] rounded px-3 py-2 text-sm text-[#e2e8f0] placeholder-[#4a5568] focus:outline-none focus:border-[#4a8fff]/50"
              />
              <input
                type="text"
                placeholder="Title / role"
                value={entry.title}
                onChange={e => updateEntry(idx, 'title', e.target.value)}
                className="flex-1 bg-[#0d1117] border border-[rgba(255,255,255,0.07)] rounded px-3 py-2 text-sm text-[#e2e8f0] placeholder-[#4a5568] focus:outline-none focus:border-[#4a8fff]/50"
              />
              <button
                onClick={() => removeEntry(idx)}
                className="px-2 py-2 text-[#4a5568] hover:text-[#f87171] transition-colors text-sm"
                title="Remove"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
        <button
          onClick={addEntry}
          className="mt-3 text-xs text-[#4a8fff] hover:text-[#6ba3ff] transition-colors"
        >
          + Add person
        </button>
      </Section>
      <SaveBar saving={saving} saved={saved} error={error} onSave={handleSave} label="Save" />
    </div>
  )
}

// ADR-124 Gate D1: AI deployer-input section. project_level block (always shown) +
// one per-service block per detected AI service. Writes ai_config JSONB (migration
// 023 schema). Selection over free text: model + purpose dropdowns, tri-state
// selects for training_data/logging. Empty fields stay empty — the KI-document gap
// markers surface what is missing. (Accordion + polished toggles = Gate D2.)

// Curated LLM list for the model dropdown (provider-grouped). "Eigenes Modell" →
// free-text reveal; the custom value passes 1:1 into the doc (no normalization).
const MODEL_GROUPS: { group: string; models: string[] }[] = [
  { group: 'OpenAI', models: ['GPT-4o', 'GPT-4o mini', 'GPT-4.1', 'o3 / o4-mini'] },
  { group: 'Anthropic', models: ['Claude Opus 4', 'Claude Sonnet 4', 'Claude Haiku'] },
  { group: 'Google', models: ['Gemini 2.5 Pro', 'Gemini 2.5 Flash'] },
  { group: 'Meta', models: ['Llama 4'] },
  { group: 'Mistral', models: ['Mistral Large', 'Mistral Small'] },
  { group: 'DeepSeek', models: ['DeepSeek-V3 / R1'] },
  { group: 'Open / Self-hosted', models: ['Gemma (Ollama)', 'Qwen'] },
]
const ALL_MODEL_NAMES = new Set(MODEL_GROUPS.flatMap(g => g.models))
const MODEL_CUSTOM = '__custom__'

// purpose dropdown groups (by UseCase.risk_level). Unacceptable (Art. 5) is rendered
// in a separate, clearly-labelled prohibited group — never as a normal purpose.
const RISK_GROUPS: { key: string; label: string }[] = [
  { key: 'High', label: 'High-risk (Annex III)' },
  { key: 'Limited', label: 'Limited risk (transparency obligations)' },
  { key: 'Minimal', label: 'Minimal risk' },
]
const PROHIBITED_GROUP_LABEL = '⚠ Prohibited AI practices (Art. 5 EU AI Act)'

// tri-state bool <-> <select> value
const boolToSel = (v: boolean | null | undefined): string => (v === true ? 'yes' : v === false ? 'no' : '')
const selToBool = (v: string): boolean | null => (v === 'yes' ? true : v === 'no' ? false : null)

function AISection({
  projectName,
  initialAiConfig,
  onSaved,
}: {
  projectName: string
  initialAiConfig: AiConfig
  onSaved: (ai: AiConfig) => void
}) {
  const [projectLevel, setProjectLevel] = useState<AiConfig['project_level']>(initialAiConfig.project_level ?? {})
  const [perService, setPerService] = useState<AiConfig['per_service']>(initialAiConfig.per_service ?? {})
  // ADR-124 Gate F: serviceNames = rendered union (scan finds ∪ saved per_service ∪ manually
  // added), drivable by add/delete. No delete-memory — a deleted scan find reappears on the
  // next scan (if the scanner sees it, the code uses it → showing it is the safe side).
  const [serviceNames, setServiceNames] = useState<string[]>(Object.keys(initialAiConfig.per_service ?? {}))
  const [scanFoundNames, setScanFoundNames] = useState<Set<string>>(new Set())  // origin badge
  const [scrollToName, setScrollToName] = useState<string | null>(null)         // scroll-to after add
  const [aiProviders, setAiProviders] = useState<string[]>([])
  const [useCases, setUseCases] = useState<UseCaseOption[]>([])
  const [customModel, setCustomModel] = useState<Record<string, boolean>>({})
  const [openSvc, setOpenSvc] = useState<string | null>(null)        // single-expand accordion
  const [openDetails, setOpenDetails] = useState<Record<string, boolean>>({})  // "Details (optional)"
  const [loadingServices, setLoadingServices] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    const savedKeys = Object.keys(initialAiConfig.per_service ?? {})
    getAiServices(projectName)
      .then(svcs => {
        if (!active) return
        setScanFoundNames(new Set(svcs.map(s => s.name)))
        const merged = [...savedKeys]
        for (const s of svcs) if (!merged.includes(s.name)) merged.push(s.name)
        setServiceNames(merged)
        setOpenSvc(merged[0] ?? null)
      })
      .finally(() => { if (active) setLoadingServices(false) })
    getUseCases().then(ucs => { if (active) setUseCases(ucs) })
    getAiProviders().then(ps => { if (active) setAiProviders(ps) })
    return () => { active = false }
  }, [projectName])

  // ADR-124 Gate F iter 3: after add, scroll the (just-rendered) card into view so the
  // reaction is where the eye is — fixes the "added card off-screen, no feedback" bug.
  useEffect(() => {
    if (!scrollToName) return
    const id = requestAnimationFrame(() =>
      document.getElementById(`ai-card-${scrollToName}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' }))
    return () => cancelAnimationFrame(id)
  }, [scrollToName])

  // ADR-124 Gate F: add a provider card (dup-safe — opens the existing one instead of
  // creating a second), or delete a card (removes from the in-memory list + per_service).
  const addService = (name: string) => {
    if (!name) return
    if (serviceNames.includes(name)) { setOpenSvc(name); setScrollToName(name); return }
    setServiceNames(prev => [...prev, name])   // append → end, directly above the dropdown
    setPerService(p => ({ ...p, [name]: p[name] ?? {} }))
    setOpenSvc(name)
    setScrollToName(name)
  }
  const removeService = (name: string) => {
    setServiceNames(prev => prev.filter(n => n !== name))
    setPerService(p => { const c = { ...p }; delete c[name]; return c })
    setOpenSvc(o => (o === name ? null : o))
  }

  function updateProjectLevel<K extends keyof AiConfig['project_level']>(field: K, value: AiConfig['project_level'][K]) {
    setProjectLevel(p => ({ ...p, [field]: value }))
  }
  function updateService<K extends keyof AiServiceFields>(svc: string, field: K, value: AiServiceFields[K]) {
    setPerService(p => ({ ...p, [svc]: { ...(p[svc] ?? {}), [field]: value } }))
  }

  // a value counts as "filled" when set: strings non-empty, booleans not null/undefined.
  const isFilled = (v: unknown) => (typeof v === 'boolean' ? true : Boolean(v))
  const plFilled = (['operative_responsible', 'tech_responsible', 'ai_literacy_measures'] as const)
    .filter(k => isFilled(projectLevel[k])).length
  const svcFilled = (name: string) =>
    (['model', 'purpose', 'user_groups', 'usage_limits', 'training_data', 'logging'] as const)
      .filter(k => isFilled((perService[name] ?? {})[k])).length
  // ADR-124 Gate F iter 2: only offer providers not already added (dup-guard stays as net).
  const availableProviders = aiProviders.filter(p => !serviceNames.includes(p))

  const handleSave = async () => {
    setSaving(true); setSaved(false); setError(null)
    const ai: AiConfig = { project_level: projectLevel, per_service: perService }
    try {
      await saveProjectAi(projectName, ai)
      onSaved(ai)
      setSaved(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const labelClass = 'block text-xs text-[#4a5568] mb-1'
  const purposeTitle = (type?: string) => (type ? useCases.find(u => u.type === type)?.title_de : undefined)
  // ADR-102: an unset field becomes a gap marker in the document — show ⊘ (muted, not red),
  // so it reads as "will be flagged", not as a required field applying pressure.
  const gapMark = (set: boolean) =>
    set ? null : <span className="ml-1 text-[#4a5568]" title="Empty → flagged as a gap (⊘) in the document">⊘</span>

  return (
    <div className="space-y-6 max-w-2xl">
      <Section title="AI responsibility (project-wide)"
               subtitle="EU AI Act — applies to all AI systems of this project.">
        <div className="flex items-center justify-between gap-4">
          <p className="text-xs text-[#4a5568]">
            Flows into: AI Act Manifest §1 (responsible persons) · AI Policy
          </p>
          <span className={`text-xs tabular-nums shrink-0 ${plFilled === 3 ? 'text-[#4a8fff]' : 'text-[#4a5568]'}`}>
            {plFilled === 3 && '✓ '}{plFilled}/3
          </span>
        </div>
        <div>
          <label className={labelClass}>Operational AI responsibility</label>
          <input type="text" className={inputClass} placeholder="Name / Funktion"
            value={projectLevel.operative_responsible ?? ''}
            onChange={e => updateProjectLevel('operative_responsible', e.target.value)} />
          <Hint>Who steers day-to-day AI use? Person or function (e.g. “Misty Knight, Head of Eng” or “Head of HR”).</Hint>
        </div>
        <div>
          <label className={labelClass}>Technical AI responsibility</label>
          <input type="text" className={inputClass} placeholder="Name / Funktion"
            value={projectLevel.tech_responsible ?? ''}
            onChange={e => updateProjectLevel('tech_responsible', e.target.value)} />
          <Hint>Who is responsible for running the AI system technically? Person or function.</Hint>
        </div>
        <div>
          <label className={labelClass}>AI literacy / training (Art. 4)</label>
          <select className={inputClass}
            value={boolToSel(projectLevel.ai_literacy_measures)}
            onChange={e => updateProjectLevel('ai_literacy_measures', selToBool(e.target.value))}>
            <option value="">— select —</option>
            <option value="yes">Yes — staff are trained / made aware</option>
            <option value="no">No — not implemented yet</option>
          </select>
          <Hint>Art. 4 EU AI Act applies since 2 Feb 2025 to providers and deployers: staff need a sufficient level of AI literacy.</Hint>
        </div>
        <div>
          <label className={labelClass}>Note on AI literacy (optional)</label>
          <input type="text" className={inputClass} placeholder="e.g. onboarding training + annual refresher"
            value={projectLevel.ai_literacy_note ?? ''}
            onChange={e => updateProjectLevel('ai_literacy_note', e.target.value)} />
          <Hint>How is AI literacy ensured? Free text.</Hint>
        </div>
      </Section>

      <Section title="AI systems"
               subtitle="Details per detected AI service.">
        <p className="text-xs text-[#4a5568]">
          Flows into: AI System Documentation · EU AI Act Art. 11/12
        </p>
        {loadingServices ? (
          <p className="text-xs text-[#4a5568]">Loading AI services …</p>
        ) : (
          <>
          {serviceNames.length === 0 ? (
            <p className="text-xs text-[#4a5568]">
              No AI services yet — run a scan or add a provider below.
            </p>
          ) : (
          <div className="space-y-2">
            {serviceNames.map(name => {
              const f = perService[name] ?? {}
              const n = svcFilled(name)
              const open = openSvc === name
              const pt = purposeTitle(f.purpose)
              const typingCustom = !!customModel[name]                                   // input visible
              const isCustomValue = !!f.model && !ALL_MODEL_NAMES.has(f.model)            // saved custom name
              return (
                <div key={name} id={`ai-card-${name}`} className="border border-[rgba(255,255,255,0.07)] rounded">
                  {/* collapsed ledger row (54px) — Dienst · Modell · Zweck · Status */}
                  <button type="button"
                    onClick={() => setOpenSvc(o => (o === name ? null : name))}
                    className="w-full h-[54px] px-4 flex items-center justify-between gap-4 text-left hover:bg-[#111622] transition-colors">
                    <span className="flex items-center gap-3 min-w-0">
                      <span className="text-[#4a5568] text-xs shrink-0">{open ? '▾' : '▸'}</span>
                      <span className="text-sm font-medium text-[#e2e8f0] shrink-0">{name}</span>
                      <span className="text-xs text-[#4a5568] font-mono truncate">
                        {(f.model || '—')} · {pt || '—'}
                      </span>
                    </span>
                    <span className={`text-xs tabular-nums shrink-0 ${n === 6 ? 'text-[#4a8fff]' : 'text-[#4a5568]'}`}>
                      {n === 6 ? '✓ fertig' : `${6 - n} offen`}
                    </span>
                  </button>

                  {open && (
                    <div className="px-4 pb-4 pt-1 space-y-5 border-t border-[rgba(255,255,255,0.07)]">
                      {/* origin + remove (top, ADR-124 Gate F iter 2) */}
                      <div className="flex items-center justify-between gap-3 pt-3">
                        <span className="text-xs text-[#4a5568]">
                          {scanFoundNames.has(name)
                            ? 'Found by the scan — the code uses this service.'
                            : 'Added manually.'}
                        </span>
                        <button type="button" onClick={() => removeService(name)}
                          title="Scanner false positive? Remove it here."
                          className="text-xs text-[#4a8fff] hover:underline shrink-0">
                          Not an AI service? → Remove
                        </button>
                      </div>

                      {/* Zweck → Modell — Auswahl zuerst (geringste kognitive Last) */}
                      <div className="space-y-3">
                        <div>
                          <label className={labelClass}>What is it used for? {gapMark(isFilled(f.purpose))}</label>
                          <select className={inputClass}
                            value={f.purpose ?? ''}
                            onChange={e => updateService(name, 'purpose', e.target.value)}>
                            <option value="">— select —</option>
                            {RISK_GROUPS.map(rg => {
                              const items = useCases.filter(u => u.risk_level === rg.key)
                              return items.length === 0 ? null : (
                                <optgroup key={rg.key} label={rg.label}>
                                  {items.map(u => <option key={u.type} value={u.type}>{u.title_de}</option>)}
                                </optgroup>
                              )
                            })}
                            {useCases.some(u => u.risk_level === 'Unacceptable') && (
                              <optgroup label={PROHIBITED_GROUP_LABEL}>
                                {useCases.filter(u => u.risk_level === 'Unacceptable')
                                  .map(u => <option key={u.type} value={u.type}>{u.title_de}</option>)}
                              </optgroup>
                            )}
                          </select>
                          <Hint>Choose the use case that fits best — it determines the risk class.</Hint>
                        </div>
                        <div>
                          <label className={labelClass}>Model {gapMark(isFilled(f.model))}</label>
                          <select className={inputClass}
                            value={typingCustom ? MODEL_CUSTOM : (f.model ?? '')}
                            onChange={e => {
                              const v = e.target.value
                              if (v === MODEL_CUSTOM) {
                                setCustomModel(c => ({ ...c, [name]: true }))
                                updateService(name, 'model', '')
                              } else {
                                setCustomModel(c => ({ ...c, [name]: false }))
                                updateService(name, 'model', v)
                              }
                            }}>
                            <option value="">— select —</option>
                            {/* a saved custom model reattaches as a normal selected option */}
                            {isCustomValue && !typingCustom && <option value={f.model}>{f.model}</option>}
                            {MODEL_GROUPS.map(g => (
                              <optgroup key={g.group} label={g.group}>
                                {g.models.map(m => <option key={m} value={m}>{m}</option>)}
                              </optgroup>
                            ))}
                            <option value={MODEL_CUSTOM}>Custom model …</option>
                          </select>
                          {typingCustom && (
                            <input type="text" className={`${inputClass} mt-2`} placeholder="Model name" autoFocus
                              value={f.model ?? ''}
                              onChange={e => updateService(name, 'model', e.target.value)}
                              onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); (e.target as HTMLInputElement).blur() } }}
                              onBlur={() => { if ((f.model ?? '').trim()) setCustomModel(c => ({ ...c, [name]: false })) }} />
                          )}
                          <Hint>Which AI model do you use with this service? Not in the list → “Custom model”.</Hint>
                        </div>
                      </div>

                      {/* yes/no toggles */}
                      <div className="space-y-3">
                        <div>
                          <label className={labelClass}>Own training data used? {gapMark(isFilled(f.training_data))}</label>
                          <select className={inputClass}
                            value={boolToSel(f.training_data)}
                            onChange={e => updateService(name, 'training_data', selToBool(e.target.value))}>
                            <option value="">— select —</option>
                            <option value="yes">Yes</option>
                            <option value="no">No</option>
                          </select>
                          <Hint>Did you use your own data to train or fine-tune the model? Mere use via the API does not count.</Hint>
                        </div>
                        <div>
                          <label className={labelClass}>Is usage logged? {gapMark(isFilled(f.logging))}</label>
                          <select className={inputClass}
                            value={boolToSel(f.logging)}
                            onChange={e => updateService(name, 'logging', selToBool(e.target.value))}>
                            <option value="">— select —</option>
                            <option value="yes">Yes</option>
                            <option value="no">No</option>
                          </select>
                          <Hint>Are logs kept of who uses the system and when? Relevant for the audit trail (EU AI Act Art. 26(6)).</Hint>
                        </div>
                      </div>

                      {/* Details (optional) — eingeklappt by default */}
                      <div>
                        <button type="button"
                          onClick={() => setOpenDetails(d => ({ ...d, [name]: !d[name] }))}
                          className="text-xs text-[#4a5568] hover:text-[#e2e8f0] transition-colors">
                          {openDetails[name] ? '▾' : '▸'} Details (optional)
                        </button>
                        {openDetails[name] && (
                          <div className="mt-3 space-y-3">
                            <div>
                              <label className={labelClass}>User groups {gapMark(isFilled(f.user_groups))}</label>
                              <textarea className={inputClass} rows={2}
                                value={f.user_groups ?? ''}
                                onChange={e => updateService(name, 'user_groups', e.target.value)} />
                              <Hint>Who in the company uses the system? E.g. “HR recruiting team”, “support team”.</Hint>
                            </div>
                            <div>
                              <label className={labelClass}>System limits {gapMark(isFilled(f.usage_limits))}</label>
                              <textarea className={inputClass} rows={2}
                                value={f.usage_limits ?? ''}
                                onChange={e => updateService(name, 'usage_limits', e.target.value)} />
                              <Hint>What must the system not do? E.g. “no automated final decision”.</Hint>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
          )}
          <div className="pt-4 mt-1 border-t border-[rgba(255,255,255,0.07)] space-y-2">
            <h3 className="text-sm font-medium text-[#e2e8f0]">KI-Anbieter</h3>
            {availableProviders.length > 0 ? (
              <div>
                <label className={labelClass}>Add more AI providers</label>
                <select className={inputClass} value=""
                  onChange={e => addService(e.target.value)}>
                  <option value="">+ Select AI provider …</option>
                  {availableProviders.map(p => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
                <Hint>The scan adds detected services automatically. Add more here — services detected on the next scan reappear as well (no deletion memory).</Hint>
              </div>
            ) : (
              <p className="text-xs text-[#4a5568]">Alle bekannten KI-Anbieter sind bereits angelegt.</p>
            )}
          </div>
          </>
        )}
      </Section>

      <SaveBar saving={saving} saved={saved} error={error} onSave={handleSave} label="SAVE AI DETAILS" />
    </div>
  )
}
