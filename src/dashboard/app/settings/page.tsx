'use client'
// Legacy settings page — still reachable via /settings/?project=<name>.
// Superseded by the project workspace (/project/<name>/<section>).
// Kept for backwards compat with any bookmarked URLs.

import { Suspense, useCallback, useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Sidebar from '../../components/Sidebar'
import { useReadiness } from '../../components/useReadiness'
import {
  getProjectConfig,
  getProjectSetup,
  saveProjectCompany,
  saveProjectSetup,
  triggerScan,
  type ProjectSetupPayload,
  type RetentionPolicyIn,
} from '../../lib/api'

// ── Curated HostingProvider list — mirror scripts/seed_both.py ADR_076_HOSTING ─

const HOSTING_PROVIDERS = [
  'AWS', 'GCP', 'Azure', 'Hetzner', 'IONOS', 'OVH', 'Strato',
  'Supabase Cloud', 'Vercel', 'Railway', 'Fly.io', 'Cloudflare',
]

// ── Shared styles — lifted from setup/page.tsx to keep the visual language ────

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

// ── Form state ─────────────────────────────────────────────────────────────────

type Form = {
  // Company (project_config)
  company_name: string
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

  // Hosting (project_setups)
  on_prem: boolean
  hosting_provider: string
  hosting_region: string

  retention_policies: RetentionPolicyIn[]
}

const EMPTY: Form = {
  company_name: '', legal_form: '', address: '', zip_code: '', city: '',
  contact_email: '', website_url: '',
  responsible_name: '', responsible_title: '',
  register_court: '', register_number: '',
  dpo_name: '', dpo_email: '',
  on_prem: false, hosting_provider: '', hosting_region: '',
  retention_policies: [],
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function SettingsPage() {
  return (
    <Suspense fallback={<Shell title="Project settings"><div /></Shell>}>
      <SettingsPageInner />
    </Suspense>
  )
}

function SettingsPageInner() {
  const searchParams = useSearchParams()
  // First-start gate for the rescan button (server enforces the same via 503)
  const { readiness } = useReadiness()
  const preparing = readiness ? !readiness.ready : false
  const router = useRouter()
  const projectName = searchParams.get('project') || ''

  const [form, setForm] = useState<Form>(EMPTY)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastRevision, setLastRevision] = useState<string | null>(null)

  const update = useCallback(<K extends keyof Form>(k: K, v: Form[K]) => {
    setForm(p => ({ ...p, [k]: v }))
  }, [])

  const updateRetention = useCallback(
    (idx: number, key: keyof RetentionPolicyIn, value: string) => {
      setForm(p => {
        const next = [...p.retention_policies]
        const row = { ...next[idx] }
        if (key === 'duration_days') {
          const n = parseInt(value, 10)
          row.duration_days = Number.isFinite(n) ? n : null
        } else if (key === 'category' || key === 'duration_raw') {
          row[key] = value
        }
        next[idx] = row
        return { ...p, retention_policies: next }
      })
    },
    []
  )

  const addRetention = useCallback(() => {
    setForm(p => ({
      ...p,
      retention_policies: [
        ...p.retention_policies,
        { category: '', duration_days: null, duration_raw: '', source: 'setup' },
      ],
    }))
  }, [])

  const removeRetention = useCallback((idx: number) => {
    setForm(p => ({
      ...p,
      retention_policies: p.retention_policies.filter((_, i) => i !== idx),
    }))
  }, [])

  // Load both tables on mount. Setup wins for DPO overlap.
  useEffect(() => {
    if (!projectName) { setLoading(false); return }
    Promise.all([
      getProjectConfig(projectName),
      getProjectSetup(projectName),
    ])
      .then(([config, setupRes]) => {
        const setup = setupRes.setup
        const next: Form = { ...EMPTY }
        if (config) {
          next.company_name      = config.company_name ?? ''
          next.legal_form        = config.legal_form ?? ''
          next.address           = config.address ?? ''
          next.zip_code          = config.zip_code ?? ''
          next.city              = config.city ?? ''
          next.contact_email     = config.contact_email ?? ''
          next.website_url       = config.website_url ?? ''
          next.responsible_name  = config.responsible_name ?? ''
          next.responsible_title = config.responsible_title ?? ''
          next.register_court    = config.register_court ?? ''
          next.register_number   = config.register_number ?? ''
          next.dpo_name          = config.dpo_name ?? ''
          next.dpo_email         = config.dpo_email ?? ''
        }
        if (setup) {
          next.on_prem          = setup.on_prem ?? false
          next.hosting_provider = setup.hosting_provider ?? ''
          next.hosting_region   = setup.hosting_region ?? ''
        }
        next.retention_policies = (setupRes.retention_policies || [])
          .filter(r => r.source === 'setup')
          .map(r => ({
            category: r.category, duration_days: r.duration_days,
            duration_raw: r.duration_raw, source: 'setup',
          }))
        setForm(next)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [projectName])

  // Save: two parallel POSTs, then triggerScan + redirect.
  const handleSave = async () => {
    if (!projectName) return
    setSaving(true)
    setError(null)

    const configPayload: Record<string, string | null> = {
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
    }

    const setupPayload: ProjectSetupPayload = {
      on_prem:           form.on_prem,
      hosting_provider:  form.hosting_provider.trim() || null,
      hosting_region:    form.hosting_region.trim() || null,
      retention_policies: form.retention_policies
        .filter(r => r.category.trim() !== '')
        .map(r => ({ ...r, source: 'setup' as const })),
      created_by: 'dashboard',
    }

    try {
      const [configRes, setupRes] = await Promise.all([
        saveProjectCompany(configPayload),
        saveProjectSetup(projectName, setupPayload),
      ])
      if (configRes?.detail) {
        throw new Error(`config save failed: ${extractDetail(configRes.detail)}`)
      }
      if ('detail' in setupRes) {
        throw new Error(`setup save failed: ${extractDetail(setupRes.detail)}`)
      }
      setLastRevision(setupRes.revision_id)

      const scan = await triggerScan(projectName, 'setup')
      if (scan.ok && scan.scan_run_id) {
        const q = new URLSearchParams({ project: projectName, run: scan.scan_run_id })
        router.push(`/scan?${q.toString()}`)
      } else {
        if (scan.error) setError(scan.error)
        setSaving(false)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setSaving(false)
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────

  if (!projectName) {
    return (
      <Shell title="Project settings">
        <div className="max-w-2xl px-8 py-6 text-sm text-[#f87171]">
          Missing <span className="font-mono">project</span> query parameter.
          Open via <span className="font-mono">/settings/?project=&lt;name&gt;</span>.
        </div>
      </Shell>
    )
  }

  if (loading) {
    return (
      <Shell title={projectName}>
        <div className="max-w-2xl px-8 py-6 text-sm text-[#4a5568]">Loading project settings…</div>
      </Shell>
    )
  }

  return (
    <Shell title={projectName} subtitle="Edit company info, hosting, DPO and retention policies">
      <div className="max-w-3xl px-8 py-6 space-y-10">

        {/* ── Company (project_config) ────────────────────────────────────── */}
        <Section title="Company" subtitle="Written to project_config. Flows into every doc header.">
          <Grid2>
            <Field label="Company name">
              <input value={form.company_name} onChange={e => update('company_name', e.target.value)}
                placeholder="ACME GmbH" className={inputClass} />
            </Field>
            <Field label="Legal form">
              <input value={form.legal_form} onChange={e => update('legal_form', e.target.value)}
                placeholder="GmbH" className={inputClass} />
            </Field>
          </Grid2>
          <Field label="Address">
            <input value={form.address} onChange={e => update('address', e.target.value)}
              placeholder="Example Street 1" className={inputClass} />
          </Field>
          <Grid2>
            <Field label="ZIP">
              <input value={form.zip_code} onChange={e => update('zip_code', e.target.value)}
                placeholder="10115" className={inputClass} />
            </Field>
            <Field label="City">
              <input value={form.city} onChange={e => update('city', e.target.value)}
                placeholder="Berlin" className={inputClass} />
            </Field>
          </Grid2>
          <Grid2>
            <Field label="Contact email">
              <input type="email" value={form.contact_email}
                onChange={e => update('contact_email', e.target.value)}
                placeholder="hello@acme.test" className={inputClass} />
            </Field>
            <Field label="Website">
              <input type="url" value={form.website_url}
                onChange={e => update('website_url', e.target.value)}
                placeholder="https://acme.test" className={inputClass} />
            </Field>
          </Grid2>
          <Grid2>
            <Field label="Responsible person">
              <input value={form.responsible_name}
                onChange={e => update('responsible_name', e.target.value)}
                placeholder="Max Muster" className={inputClass} />
            </Field>
            <Field label="Title">
              <input value={form.responsible_title}
                onChange={e => update('responsible_title', e.target.value)}
                placeholder="CEO" className={inputClass} />
            </Field>
          </Grid2>
          <Grid2>
            <Field label="Register court">
              <input value={form.register_court}
                onChange={e => update('register_court', e.target.value)}
                placeholder="Amtsgericht Berlin" className={inputClass} />
            </Field>
            <Field label="Register number">
              <input value={form.register_number}
                onChange={e => update('register_number', e.target.value)}
                placeholder="HRB 123456" className={inputClass} />
            </Field>
          </Grid2>
        </Section>

        {/* ── DPO ──────────────────────────────────────────────────────────── */}
        <Section title="Data Protection Officer"
          subtitle="Saved to project_config. Flows into the AVV and the privacy policy.">
          <Grid2>
            <Field label="Name">
              <input value={form.dpo_name}
                onChange={e => update('dpo_name', e.target.value)}
                placeholder="Thomas Rehmer" className={inputClass} />
            </Field>
            <Field label="Email">
              <input type="email" value={form.dpo_email}
                onChange={e => update('dpo_email', e.target.value)}
                placeholder="dpo@example.com" className={inputClass} />
            </Field>
          </Grid2>
        </Section>

        {/* ── Hosting (project_setups) ────────────────────────────────────── */}
        <Section title="Hosting"
          subtitle="Determines the ⊘ delegation block in TOM § 1.1 (physical access control).">
          <Toggle
            label="On-premise"
            description="We run our own data centre. When off, physical controls are delegated to the hosting provider."
            checked={form.on_prem}
            onChange={v => update('on_prem', v)}
          />
          {!form.on_prem && (
            <>
              <Field label="Hosting provider">
                <select value={form.hosting_provider}
                  onChange={e => update('hosting_provider', e.target.value)}
                  className={inputClass}>
                  <option value="">— select provider —</option>
                  {HOSTING_PROVIDERS.map(p => (<option key={p} value={p}>{p}</option>))}
                </select>
                <Hint>
                  Curated list matches the HostingProvider seed in Neo4j (ADR-076).
                  SOC 2 / ISO 27001 metadata flows into the delegation text.
                </Hint>
              </Field>
              <Field label="Region">
                <input value={form.hosting_region}
                  onChange={e => update('hosting_region', e.target.value)}
                  placeholder="eu-central-1" className={inputClass} />
              </Field>
            </>
          )}
        </Section>

        {/* ── Retention policies ──────────────────────────────────────────── */}
        <Section title="Retention policies"
          subtitle="Flows into the privacy policy + VVT. Only 'setup' rows are edited here — code/firecrawl entries stay untouched.">
          {form.retention_policies.length === 0 && (
            <div className="text-xs text-[#4a5568] mb-3">
              No retention policies defined yet.
            </div>
          )}
          {form.retention_policies.map((rp, idx) => (
            <div key={idx} className="grid grid-cols-[2fr_1fr_1fr_auto] gap-2 mb-2">
              <input value={rp.category}
                onChange={e => updateRetention(idx, 'category', e.target.value)}
                placeholder="Server logfiles" className={inputClass} />
              <input value={rp.duration_days ?? ''}
                onChange={e => updateRetention(idx, 'duration_days', e.target.value)}
                placeholder="Days" className={inputClass} inputMode="numeric" />
              <input value={rp.duration_raw}
                onChange={e => updateRetention(idx, 'duration_raw', e.target.value)}
                placeholder="7 days" className={inputClass} />
              <button type="button" onClick={() => removeRetention(idx)}
                className="text-[#f87171] hover:text-[#fca5a5] text-lg w-8 h-full flex items-center justify-center cursor-pointer"
                aria-label="Remove">×</button>
            </div>
          ))}
          <button type="button" onClick={addRetention} className={btnSecondary}>
            + Add retention policy
          </button>
        </Section>

        {/* ── Save ────────────────────────────────────────────────────────── */}
        <div className="pt-4 border-t border-[#1e2640] flex items-center justify-between">
          <div className="text-xs text-[#4a5568]">
            {lastRevision
              ? <>Last saved revision <span className="font-mono">{lastRevision.slice(0, 8)}</span></>
              : <>Saves Company + Setup in parallel, then triggers a rescan.</>
            }
          </div>
          <div className="flex items-center gap-3">
            {error && (<span className="text-xs text-[#f87171] max-w-md truncate" title={error}>{error}</span>)}
            <button
              onClick={handleSave}
              disabled={saving || preparing}
              title={preparing ? 'System preparing — see the status card on the dashboard' : undefined}
              className={btnPrimary}
            >
              {saving ? 'SAVING…' : preparing ? 'SYSTEM PREPARING…' : 'SAVE & RESCAN \u2192'}
            </button>
          </div>
        </div>
      </div>
    </Shell>
  )
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function extractDetail(detail: unknown): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return JSON.stringify(detail)
  return String(detail)
}

function Shell({
  title, subtitle, children,
}: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-base)', display: 'flex' }}>
      <Sidebar />
      <main style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          padding: '40px 56px 0',
          borderBottom: '1px solid var(--border-default)',
        }}>
          <h1 style={{
            fontSize: '28px', fontWeight: 700,
            color: 'var(--text-primary)',
            margin: '0 0 4px', letterSpacing: '-0.02em',
          }}>{title}</h1>
          <p style={{
            fontSize: '13px',
            color: 'var(--text-muted)',
            fontFamily: 'ui-monospace, monospace',
            margin: '0 0 20px',
          }}>{subtitle || 'Project settings'}</p>
        </div>
        {children}
      </main>
    </div>
  )
}

function Section({
  title, subtitle, children,
}: { title: string; subtitle?: string; children: React.ReactNode }) {
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

function Grid2({ children }: { children: React.ReactNode }) {
  return <div className="grid grid-cols-2 gap-4">{children}</div>
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

function Toggle({
  label, description, checked, onChange,
}: {
  label: string
  description?: string
  checked: boolean
  onChange: (v: boolean) => void
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
