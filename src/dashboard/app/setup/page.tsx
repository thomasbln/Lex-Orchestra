'use client'
import { useState, useEffect, useCallback, useRef } from 'react'
import {
  getProjectConfig,
  getProjectRepos,
  saveProjectConfig,
  saveProjectCompany,
  saveProjectRepos,
  notifyConfigComplete,
  triggerScan,
  extractImpressum,
  type RepoEntry,
} from '../../lib/api'
import Sidebar from '../../components/Sidebar'
import { useReadiness } from '../../components/useReadiness'

// ── Types ──────────────────────────────────────────────────────────────────────

type WizardData = {
  project_name: string
  company_name: string
  legal_form: string
  contact_email: string
  address: string
  zip_code: string
  city: string
  country: string
  website_url: string
  responsible_name: string
  responsible_title: string
  dpo_name: string
  dpo_email: string
  doc_language: 'de' | 'en'
}

const EMPTY: WizardData = {
  project_name: '',
  company_name: '',
  legal_form: '',
  contact_email: '',
  address: '',
  zip_code: '',
  city: '',
  country: 'Germany',
  website_url: '',
  responsible_name: '',
  responsible_title: '',
  dpo_name: '',
  dpo_email: '',
  doc_language: 'de',
}

const STEPS = ['projekt', 'repos', 'company', 'complete'] as const
type Step = (typeof STEPS)[number]

const STEP_LABELS: Record<Step, string> = {
  projekt: 'PROJECT',
  repos: 'REPOSITORIES',
  company: 'COMPANY',
  complete: 'SUMMARY',
}

// ── Shared input style ─────────────────────────────────────────────────────────

const inputClass =
  'w-full bg-[#0a0d14] border border-[#1e2640] rounded px-4 py-2.5 text-sm ' +
  'text-white placeholder-[#4a5568] outline-none transition-all cursor-text ' +
  'focus:shadow-[0_0_0_1px_#4a8fff,0_0_8px_rgba(74,143,255,0.15)]'

const btnPrimary =
  'bg-[#4a8fff] disabled:bg-[#1e2640] text-white disabled:text-[#4a5568] ' +
  'px-6 py-2 rounded-sm text-sm tracking-wider transition-all cursor-pointer ' +
  'disabled:cursor-not-allowed'

const EXAMPLE_REPO_URL = 'https://github.com/thomasbln/lex-orchestra-example-app'

const CHECK_REPO_BASE = typeof window !== 'undefined'
  ? `${window.location.protocol}//${window.location.hostname}:8001`
  : 'http://lex-agent:8001'

// ── GitHub helpers ────────────────────────────────────────────────────────────

function parseGitHubUrl(url: string): { owner: string; repo: string } | null {
  const match = url.trim().match(/github\.com\/([^/]+)\/([^/]+?)(?:\.git)?\/?$/)
  return match ? { owner: match[1], repo: match[2] } : null
}

type RepoCheckStatus = {
  state: 'unchecked' | 'checking' | 'ok' | 'private' | 'error'
  message: string
}

async function checkRepo(repo: RepoEntry): Promise<RepoCheckStatus> {
  if (!repo.repo_url.trim()) return { state: 'unchecked', message: '' }
  if (!parseGitHubUrl(repo.repo_url))
    return { state: 'error', message: 'Invalid GitHub URL' }
  try {
    const params = new URLSearchParams({ url: repo.repo_url })
    if (repo.github_token?.trim()) params.set('token', repo.github_token)
    const res = await fetch(`${CHECK_REPO_BASE}/utils/check-repo?${params}`)
    const data = await res.json()
    switch (data.status) {
      case 'accessible': return { state: 'ok', message: '' }
      case 'private':    return { state: 'private', message: '' }
      case 'invalid_token': return { state: 'error', message: 'Invalid token — please check' }
      default: return { state: 'error', message: data.message || 'Repository not reachable — please check the URL' }
    }
  } catch {
    // Network/CORS failure — don't alarm the user, URL will be validated during scan
    return { state: 'unchecked', message: '' }
  }
}

function sanitizeProjectName(name: string): string {
  const trimmed = name.trim()
  // If a full GitHub URL was pasted into the name field, derive the repo slug
  // instead of storing the raw URL. A slash/colon-containing name breaks every
  // path-param read endpoint (GET /config/.../{name} → 404 on encoded %2F).
  const gh = parseGitHubUrl(trimmed)
  const base = gh ? gh.repo : trimmed
  return base
    .toLowerCase()
    .replace(/[^a-z0-9._-]+/g, '-') // drop slashes, colons, spaces and other unsafe chars
    .replace(/-{2,}/g, '-')
    .replace(/^[-.]+|[-.]+$/g, '')
}

// ── Wizard Shell with Progress Timeline ────────────────────────────────────────

function WizardShell({
  currentStep,
  data,
  completedSteps,
  children,
}: {
  currentStep: Step
  data: WizardData
  completedSteps: Step[]
  children: React.ReactNode
}) {
  const currentIdx = STEPS.indexOf(currentStep) + 1
  const total = STEPS.length

  const stepValue = (step: Step): string => {
    switch (step) {
      case 'projekt': return data.project_name
      case 'repos': return ''
      case 'company': return data.company_name
      default: return ''
    }
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-base)', display: 'flex' }}>
      <Sidebar />
      <main style={{ flex: 1, minWidth: 0 }}>
        {/* Page title */}
        <div style={{
          padding: '40px 56px 0',
          borderBottom: '1px solid var(--border-default)',
          marginBottom: '0',
        }}>
          <h1 style={{
            fontSize: '28px',
            fontWeight: 700,
            color: 'var(--text-primary)',
            margin: '0 0 4px',
            letterSpacing: '-0.02em',
          }}>
            {data.project_name || 'New Project'}
          </h1>
          <p style={{
            fontSize: '13px',
            color: 'var(--text-muted)',
            fontFamily: 'ui-monospace, monospace',
            margin: '0 0 20px',
          }}>
            Project configuration
          </p>
        </div>

        <div className="max-w-4xl px-8 pt-8" style={{ padding: '32px 56px' }}>
          <div className="text-center text-xs text-[#4a5568] tracking-widest mb-8">
            {String(currentIdx).padStart(2, '0')} / {String(total).padStart(2, '0')}
          </div>
          <div className="flex gap-8">
            {/* Timeline */}
            <div className="w-52 flex-shrink-0 pt-2 hidden md:block">
              {STEPS.map((step, i) => {
                const done = completedSteps.includes(step)
                const current = step === currentStep
                const val = stepValue(step)
                return (
                  <div key={step} className="flex items-start gap-3 mb-4">
                    <div className="flex flex-col items-center">
                      <div
                        className={`w-3 h-3 rounded-full border-2 flex-shrink-0 mt-0.5 ${
                          done
                            ? 'bg-[#4ade80] border-[#4ade80]'
                            : current
                            ? 'bg-transparent border-[#4a8fff]'
                            : 'bg-transparent border-[#2d3748]'
                        }`}
                        style={current ? { boxShadow: '0 0 8px rgba(74,143,255,0.6)' } : {}}
                      />
                      {i < STEPS.length - 1 && (
                        <div className={`w-px h-8 mt-1 ${done ? 'bg-[#4ade80]' : 'bg-[#1e2640]'}`} />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div
                        className={`text-xs font-medium tracking-wider ${
                          current
                            ? 'text-white border-l-2 border-[#4a8fff] pl-2 -ml-2'
                            : done
                            ? 'text-[#64748b]'
                            : 'text-[#2d3748]'
                        }`}
                      >
                        {done && <span className="mr-1">&#10003;</span>}
                        {STEP_LABELS[step]}
                      </div>
                      {done && val && (
                        <div className="text-xs text-[#4a8fff] truncate mt-0.5">{val}</div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
            {/* Step Card */}
            <div
              className="flex-1 border border-[#1e2640] rounded-xl step-active overflow-hidden"
              style={{ background: '#111520' }}
            >
              {children}
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

// ── Step Header ────────────────────────────────────────────────────────────────

function StepHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="border-b border-[#1e2640] px-6 py-3">
      <h2 className="text-white text-lg font-medium mt-1">{title}</h2>
      {subtitle && <p className="text-xs text-[#4a5568] mt-1">{subtitle}</p>}
    </div>
  )
}

// ── Step Footer with Back ─────────────────────────────────────────────────────

function StepFooter({
  onConfirm,
  onBack,
  disabled,
  label,
}: {
  onConfirm: () => void
  onBack?: () => void
  disabled: boolean
  label?: string
}) {
  return (
    <div className="border-t border-[#1e2640] px-6 py-4 flex justify-between">
      {onBack ? (
        <button onClick={onBack} className="text-xs text-[#4a5568] hover:text-[#94a3b8] transition-colors cursor-pointer">
          &larr; Back
        </button>
      ) : (
        <div />
      )}
      <button onClick={onConfirm} disabled={disabled} className={btnPrimary}>
        {label || 'CONFIRM \u2192'}
      </button>
    </div>
  )
}

// ── Step 1: Project ───────────────────────────────────────────────────────────

function ProjectStep({
  data,
  update,
  onConfirm,
  onExampleApp,
}: {
  data: WizardData
  update: (field: keyof WizardData, value: string) => void
  onConfirm: () => void
  onExampleApp: () => void
}) {
  const raw = data.project_name
  const sanitized = sanitizeProjectName(raw)
  const willTransform = raw.trim() !== '' && raw !== sanitized

  const handleConfirm = () => {
    update('project_name', sanitized)
    onConfirm()
  }

  return (
    <div>
      <StepHeader
        title="What is your project called?"
        subtitle="Used as reference across all generated documents."
      />
      <div className="px-6 py-6 space-y-4">
        <div>
          <label className="block text-xs text-[#94a3b8] mb-1.5 uppercase tracking-wider">
            Project name
          </label>
          <input
            value={data.project_name}
            onChange={(e) => update('project_name', e.target.value)}
            placeholder="rand-industries"
            className={inputClass}
            autoFocus
          />
          {willTransform && (
            <div className="text-xs text-[#e2e8f0] mt-1.5">
              Will be saved as: <span className="font-mono">{sanitized}</span>
            </div>
          )}
          <div className="text-xs text-[#475569] mt-1">
            Lowercase, no spaces — e.g. &quot;My Project&quot; becomes &quot;my-project&quot;
          </div>
        </div>

        <div className="flex items-center gap-3 py-2">
          <div className="flex-1 border-t border-[#1e2640]" />
          <span className="text-xs text-[#4a5568]">or</span>
          <div className="flex-1 border-t border-[#1e2640]" />
        </div>

        <button
          onClick={onExampleApp}
          className="w-full border border-[#4a8fff]/40 text-[#e2e8f0] px-4 py-3 rounded-sm text-sm tracking-wider hover:bg-[#4a8fff]/10 hover:border-[#4a8fff] transition-all cursor-pointer text-left"
        >
          <span className="text-[#e2e8f0]">&#9889; Use Example App &rarr;</span>
          <div className="text-xs text-[#475569] mt-1">
            Scans Rand Industries — a fictional SaaS app. Zero input required.
          </div>
        </button>
      </div>
      <StepFooter onConfirm={handleConfirm} disabled={!data.project_name.trim()} />
    </div>
  )
}

// ── Step 2: Repositories (ADR-033) ─────────────────────────────────────────────

function ReposStep({
  repos,
  setRepos,
  onConfirm,
  onBack,
}: {
  repos: RepoEntry[]
  setRepos: (r: RepoEntry[]) => void
  onConfirm: () => void
  onBack: () => void
}) {
  const [statuses, setStatuses] = useState<Record<number, RepoCheckStatus>>({})
  const [editingTokenIdx, setEditingTokenIdx] = useState<Set<number>>(new Set())
  const debounceTimers = useRef<Record<number, ReturnType<typeof setTimeout>>>({})
  const checkGen = useRef<Record<number, number>>({})

  // Auto-check repo when URL changes (debounced)
  useEffect(() => {
    repos.forEach((repo, i) => {
      const url = repo.repo_url.trim()
      if (!url || !parseGitHubUrl(url)) return
      if (statuses[i]?.state === 'ok' || statuses[i]?.state === 'checking') return
      clearTimeout(debounceTimers.current[i])
      debounceTimers.current[i] = setTimeout(() => {
        const gen = (checkGen.current[i] = (checkGen.current[i] || 0) + 1)
        setStatuses((prev) => ({ ...prev, [i]: { state: 'checking', message: '' } }))
        checkRepo(repo).then((result) =>
          setStatuses((prev) =>
            gen === checkGen.current[i] ? { ...prev, [i]: result } : prev,
          ),
        )
      }, 600)
    })
    return () => Object.values(debounceTimers.current).forEach(clearTimeout)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [repos.map((r) => r.repo_url + r.github_token).join(',')])

  const addRepo = () =>
    setRepos([
      ...repos,
      { repo_url: '', label: `repo-${repos.length + 1}`, github_token: '', is_primary: false },
    ])
  const removeRepo = (i: number) => {
    setRepos(repos.filter((_, idx) => idx !== i))
    setStatuses((prev) => { const next = { ...prev }; delete next[i]; return next })
  }
  const setPrimary = (i: number) =>
    setRepos(repos.map((r, idx) => ({ ...r, is_primary: idx === i })))
  const updateRepo = (i: number, field: keyof RepoEntry, value: string | boolean) => {
    setRepos(repos.map((r, idx) => (idx === i ? { ...r, [field]: value } : r)))
    if (field === 'repo_url' || field === 'github_token') {
      setStatuses((prev) => ({ ...prev, [i]: { state: 'unchecked', message: '' } }))
    }
  }
  const isValid = repos.some((r) => r.repo_url.trim())
  const hasPrivateNeedingToken = Object.values(statuses).some((s) => s.state === 'private')

  const useExampleApp = (i: number) => {
    const updated = repos.map((r, idx) =>
      idx === i ? { ...r, repo_url: EXAMPLE_REPO_URL, label: 'main' } : r,
    )
    setRepos(updated)
    setStatuses((prev) => ({ ...prev, [i]: { state: 'ok', message: '' } }))
  }

  const recheckSingle = async (i: number) => {
    setStatuses((prev) => ({ ...prev, [i]: { state: 'checking', message: '' } }))
    const result = await checkRepo(repos[i])
    setStatuses((prev) => ({ ...prev, [i]: result }))
    if (result.state === 'ok') {
      setEditingTokenIdx((prev) => { const next = new Set(prev); next.delete(i); return next })
    }
  }

  const handleConfirm = () => onConfirm()

  return (
    <div>
      <StepHeader title="Where is your code?" subtitle="Multiple repos supported — backend + frontend etc." />
      <div className="px-6 py-6 space-y-4">
        {repos.map((repo, i) => {
          const st = statuses[i]
          const needsToken = st?.state === 'private'
          const isRechecking = st?.state === 'checking'
          const isVerified = st?.state === 'ok'
          const editingToken = editingTokenIdx.has(i)
          const showTokenField = needsToken || (repo.github_token && !isVerified) || editingToken
          const showMaskedToken = isVerified && repo.github_token && !editingToken
          return (
            <div
              key={i}
              className={`border rounded-lg p-4 space-y-3 ${
                isVerified ? 'border-[#4ade80]/40'
                : (st?.state === 'error' || needsToken) ? 'border-[#fbbf24]/40'
                : 'border-[#1e2640]'
              }`}
            >
              <div className="flex items-center justify-between">
                <label className="flex items-center gap-2 text-xs text-[#94a3b8] cursor-pointer">
                  <input type="radio" checked={repo.is_primary} onChange={() => setPrimary(i)} className="accent-[#4a8fff] cursor-pointer" />
                  {repo.is_primary ? 'Main Repo' : 'Additional'}
                </label>
                <div className="flex items-center gap-3">
                  {isVerified && <span className="text-xs text-[#4ade80]">&#10003; Verified</span>}
                  {repos.length > 1 && (
                    <button onClick={() => removeRepo(i)} className="text-xs text-[#4a5568] hover:text-[#f87171] cursor-pointer transition-colors">
                      Remove &times;
                    </button>
                  )}
                </div>
              </div>
              <input value={repo.repo_url} onChange={(e) => updateRepo(i, 'repo_url', e.target.value)} placeholder="https://github.com/thomasbln/lex-orchestra-example-app" className={inputClass} />
              {repo.is_primary && <div className="text-xs text-[#475569]">Your main codebase — this gets scanned</div>}
              {!repo.repo_url.trim() && (
                <div className="flex items-center gap-3">
                  <button onClick={() => useExampleApp(i)} className="text-xs text-[#e2e8f0] hover:text-white border border-[#2d3748] hover:border-[#4a8fff] px-3 py-1.5 rounded transition-all cursor-pointer">
                    Use example app &rarr;
                  </button>
                  <span className="text-xs text-[#475569]">Rand Industries — a fictional SaaS app, good for a first test scan.</span>
                </div>
              )}
              {isRechecking && <div className="text-xs text-[#4a5568]">Checking...</div>}
              {st?.state === 'error' && <div className="text-xs text-[#fbbf24]">&#9888; Could not verify — URL will be used as-is</div>}
              {needsToken && (
                <div className="text-xs text-[#fbbf24]">&#9888; Private repo — token required for scan</div>
              )}
              {showMaskedToken && (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-[#94a3b8]">Token: {'*'.repeat(Math.min((repo.github_token ?? '').length, 20))}</span>
                  <button onClick={() => setEditingTokenIdx((prev) => { const next = new Set(prev); next.add(i); return next })} className="text-xs text-[#e2e8f0] hover:text-white cursor-pointer transition-colors" title="Edit token">&#9998;</button>
                </div>
              )}
              {showTokenField && (
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <input type="password" autoComplete="off" value={repo.github_token ?? ''} onChange={(e) => updateRepo(i, 'github_token', e.target.value)} placeholder="ghp_..." className={`${inputClass} flex-1`} autoFocus />
                    <button onClick={() => recheckSingle(i)} disabled={!repo.github_token?.trim() || isRechecking} className={`${btnPrimary} flex-shrink-0 py-2.5`}>
                      {isRechecking ? 'Checking...' : 'Verify'}
                    </button>
                  </div>
                  <div className="text-xs text-[#475569]">Stored locally on your Pi only — never leaves your network.</div>
                </div>
              )}
            </div>
          )
        })}
        <button onClick={addRepo} className="w-full border border-dashed border-[#2d3748] text-[#4a5568] hover:border-[#4a8fff] hover:text-[#e2e8f0] rounded-lg py-2.5 text-xs tracking-wider transition-all cursor-pointer">
          + Add another repository
        </button>
      </div>
      <StepFooter onConfirm={handleConfirm} onBack={onBack} disabled={!isValid || hasPrivateNeedingToken} />
    </div>
  )
}

// ── Step 3: Company (merged company + address + responsible) ──────────────────

function CompanyStep({
  data,
  update,
  onConfirm,
  onBack,
}: {
  data: WizardData
  update: (field: keyof WizardData, value: string) => void
  onConfirm: () => void
  onBack: () => void
}) {
  const [scanning, setScanning] = useState(false)
  const [scanResult, setScanResult] = useState<string>('')
  const [scanFieldCount, setScanFieldCount] = useState(0)

  const handleScanWebsite = async () => {
    if (!data.website_url.trim()) return
    setScanning(true)
    setScanResult('')
    setScanFieldCount(0)
    try {
      const result = await extractImpressum(data.website_url)
      if (!result.success) {
        if (result.error === 'not_configured') {
          setScanResult('')
          setScanning(false)
          return
        }
        setScanResult('Nothing found — fill in below')
        setScanning(false)
        return
      }
      const fields = result.fields || {}
      // Map API legal_form values to select options
      const legalFormMap: Record<string, string> = {
        'UG': 'UG (haftungsbeschränkt)',
        'UG (limited liability)': 'UG (haftungsbeschränkt)',
      }
      const found: string[] = []
      for (const [key, value] of Object.entries(fields)) {
        if (value) {
          const mapped = key === 'legal_form' && legalFormMap[value as string]
            ? legalFormMap[value as string]
            : value as string
          update(key as keyof WizardData, mapped)
          found.push(key.replace(/_/g, ' '))
        }
      }
      setScanFieldCount(found.length)
      setScanResult(found.length > 0 ? `${found.length} fields found` : 'Nothing found — fill in below')
    } catch {
      setScanResult('Scan failed — fill in below')
    }
    setScanning(false)
  }

  return (
    <div>
      <StepHeader title="Company information" subtitle="Used for DPA, imprint, and privacy policy." />
      <div className="px-6 py-6 space-y-5">

        {/* Hero: auto-fill from website */}
        <div className="border border-[#4a8fff]/30 rounded-lg p-4 bg-[#4a8fff]/5">
          <div className="text-sm text-white font-medium mb-2">Auto-fill from your website</div>
          <div className="flex gap-2">
            <input
              value={data.website_url}
              onChange={(e) => update('website_url', e.target.value)}
              placeholder="https://yoursite.com"
              type="url"
              className={`${inputClass} flex-1`}
              autoFocus
            />
            <button
              onClick={handleScanWebsite}
              disabled={!data.website_url.trim() || scanning}
              className={`flex-shrink-0 ${btnPrimary} px-4 py-2.5`}
            >
              {scanning ? 'Scanning...' : 'Scan Website \u2192'}
            </button>
          </div>
          {scanResult && (
            <div className={`text-xs mt-2 ${scanFieldCount > 0 ? 'text-[#4ade80]' : 'text-[#fbbf24]'}`}>
              {scanFieldCount > 0 ? '\u2713 ' : ''}{scanResult}
            </div>
          )}
          {!scanResult && <div className="text-xs text-[#475569] mt-2">Suggestions from your imprint via Firecrawl (cloud service) — please review before saving</div>}
        </div>

        {/* Divider */}
        <div className="flex items-center gap-3">
          <div className="flex-1 border-t border-[#1e2640]" />
          <span className="text-xs text-[#4a5568]">or fill in manually</span>
          <div className="flex-1 border-t border-[#1e2640]" />
        </div>

        {/* 2-column layout */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Left column */}
          <div className="space-y-4">
            <div>
              <label className="block text-xs text-[#94a3b8] mb-1.5 uppercase tracking-wider">Company name *</label>
              <input value={data.company_name} onChange={(e) => update('company_name', e.target.value)} placeholder="Rand Industries Inc." className={inputClass} />
            </div>
            <div>
              <label className="block text-xs text-[#94a3b8] mb-1.5 uppercase tracking-wider">Legal form</label>
              <select value={data.legal_form} onChange={(e) => update('legal_form', e.target.value)} className={inputClass}>
                <option value="">Select...</option>
                <option value="GmbH">GmbH</option>
                <option value="GmbH & Co. KG">GmbH &amp; Co. KG</option>
                <option value="AG">AG</option>
                <option value="UG (haftungsbeschränkt)">UG</option>
                <option value="GbR">GbR</option>
                <option value="e.V.">e.V.</option>
                <option value="KG">KG</option>
                <option value="Inc.">Inc.</option>
                <option value="Ltd.">Ltd.</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-[#94a3b8] mb-1.5 uppercase tracking-wider">Document language</label>
              <select value={data.doc_language} onChange={(e) => update('doc_language', e.target.value === 'en' ? 'en' : 'de')} className={inputClass}>
                <option value="de">Deutsch</option>
                <option value="en">English</option>
              </select>
              <p className="mt-1 text-[11px] text-[#64748b]">
                Language of the generated legal documents — not the UI. Changeable later under Company &amp; DPO.
              </p>
            </div>
            <div>
              <label className="block text-xs text-[#94a3b8] mb-1.5 uppercase tracking-wider">Contact email *</label>
              <input value={data.contact_email} onChange={(e) => update('contact_email', e.target.value)} placeholder="legal@rand-industries.example.com" type="email" className={inputClass} />
            </div>
          </div>
          {/* Right column */}
          <div className="space-y-4">
            <div>
              <label className="block text-xs text-[#94a3b8] mb-1.5 uppercase tracking-wider">Street + number</label>
              <input value={data.address} onChange={(e) => update('address', e.target.value)} placeholder="12 Alias Lane" className={inputClass} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-[#94a3b8] mb-1.5 uppercase tracking-wider">ZIP</label>
                <input value={data.zip_code} onChange={(e) => update('zip_code', e.target.value)} placeholder="10117" className={inputClass} />
              </div>
              <div>
                <label className="block text-xs text-[#94a3b8] mb-1.5 uppercase tracking-wider">City</label>
                <input value={data.city} onChange={(e) => update('city', e.target.value)} placeholder="Berlin" className={inputClass} />
              </div>
            </div>
            <div>
              <label className="block text-xs text-[#94a3b8] mb-1.5 uppercase tracking-wider">Country</label>
              <input value={data.country} onChange={(e) => update('country', e.target.value)} placeholder="Germany" className={inputClass} />
            </div>
          </div>
        </div>

        {/* Responsible person — full width */}
        <div className="border-t border-[#1e2640] pt-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-[#94a3b8] mb-1.5 uppercase tracking-wider">Responsible person *</label>
              <input value={data.responsible_name} onChange={(e) => update('responsible_name', e.target.value)} placeholder="Misty Knight" className={inputClass} />
            </div>
            <div>
              <label className="block text-xs text-[#94a3b8] mb-1.5 uppercase tracking-wider">Title / Role</label>
              <input value={data.responsible_title} onChange={(e) => update('responsible_title', e.target.value)} placeholder="Managing Director" className={inputClass} />
            </div>
          </div>
        </div>

        {/* DPO collapsible */}
        <details className="border-t border-[#1e2640] pt-4">
          <summary className="text-xs text-[#4a5568] cursor-pointer hover:text-[#94a3b8] list-none transition-colors tracking-widest">
            &#9656; Data Protection Officer (optional)
          </summary>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3">
            <div>
              <label className="block text-xs text-[#94a3b8] mb-1.5 uppercase tracking-wider">Name</label>
              <input value={data.dpo_name} onChange={(e) => update('dpo_name', e.target.value)} placeholder="Danny Rand" className={inputClass} />
            </div>
            <div>
              <label className="block text-xs text-[#94a3b8] mb-1.5 uppercase tracking-wider">Email</label>
              <input value={data.dpo_email} onChange={(e) => update('dpo_email', e.target.value)} placeholder="dpo@rand-industries.example.com" type="email" className={inputClass} />
            </div>
          </div>
        </details>

      </div>
      <StepFooter
        onConfirm={onConfirm}
        onBack={onBack}
        disabled={!data.company_name.trim() || !data.responsible_name.trim() || !data.contact_email.trim()}
      />
    </div>
  )
}

// ── Complete Screen ────────────────────────────────────────────────────────────

function CompleteStep({
  data,
  repos,
  onSave,
  onBack,
  saving,
  saved,
  error,
}: {
  data: WizardData
  repos: RepoEntry[]
  onSave: () => void
  onBack: () => void
  saving: boolean
  saved: boolean
  error: string
}) {
  // First-start gate: block only the scan-launch, the wizard stays fillable
  const { readiness } = useReadiness()
  const preparing = readiness ? !readiness.ready : false
  const required = [
    { label: 'Company name', value: data.company_name },
    { label: 'Responsible person', value: data.responsible_name },
    { label: 'Contact email', value: data.contact_email },
    { label: 'Repository', value: repos.find((r) => r.is_primary)?.repo_url || repos[0]?.repo_url },
  ]
  const allValid = required.every((f) => f.value)

  return (
    <div>
      <div className="border-b border-[#1e2640] px-6 py-3">
        <span className="text-xs text-[#4ade80] tracking-widest">&#10003; CONFIGURATION COMPLETE</span>
      </div>
      <div className="px-6 py-6">
        <div className="space-y-2 mb-4">
          {required.map((f) => (
            <div key={f.label} className="flex items-center justify-between text-sm">
              <span className="text-[#94a3b8]">{f.label}</span>
              <span className={f.value ? 'text-[#4ade80]' : 'text-[#fbbf24]'}>
                {f.value ? <>&nbsp;&#10003; {f.value}</> : <>&nbsp;&#9888; missing</>}
              </span>
            </div>
          ))}
        </div>
        <div className="text-xs text-[#4a5568] mb-1 mt-4 tracking-widest">REPOSITORIES</div>
        <div className="border border-[#1e2640] rounded text-xs divide-y divide-[#1e2640] mb-6">
          {repos.filter((r) => r.repo_url).map((r, i) => (
            <div key={i} className="flex justify-between px-3 py-2">
              <span className="text-[#4a5568]">{r.label}{r.is_primary ? ' \u2605' : ''}</span>
              <span className="text-[#94a3b8] truncate max-w-[240px]">{r.repo_url.replace('https://github.com/', '')}</span>
            </div>
          ))}
        </div>
        {error && <div className="text-[#f87171] text-xs mb-3">{error}</div>}
        <div className="flex gap-3">
          <button onClick={onBack} className="text-xs text-[#4a5568] hover:text-[#94a3b8] transition-colors cursor-pointer px-4 py-3">
            &larr; Back
          </button>
          <button
            onClick={onSave}
            disabled={!allValid || saving || saved || preparing}
            title={preparing ? 'System preparing — see the status card on the dashboard' : undefined}
            className={`flex-1 ${btnPrimary} py-3`}
          >
            {saving ? 'Saving & starting scan...' : saved ? 'Scan started — opening status page...' : preparing ? 'SYSTEM PREPARING…' : 'SAVE & START SCAN \u2192'}
          </button>
        </div>
        {!allValid && <p className="text-xs text-[#fbbf24] mt-2 text-center">Please fill in all required fields</p>}
      </div>
    </div>
  )
}

// ── Main Page ──────────────────────────────────────────────────────────────────

export default function SetupPage() {
  const [step, setStep] = useState<Step>('projekt')
  const [data, setData] = useState<WizardData>(EMPTY)
  const [repos, setRepos] = useState<RepoEntry[]>([
    // Start empty — the user must enter their own repo, or use the explicit
    // "Use example app" button. Pre-filling the example URL caused it to be
    // scanned silently when the user entered their repo elsewhere by mistake.
    { repo_url: '', label: 'main', github_token: '', is_primary: true },
  ])
  const [completed, setCompleted] = useState<Step[]>([])
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [saveError, setSaveError] = useState('')
  const [exampleLoading, setExampleLoading] = useState(false)
  const savingRef = useRef(false)

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const project = params.get('project')
    if (!project) return
    setData((prev) => ({ ...prev, project_name: project }))
    getProjectConfig(project).then((cfg) => {
      if (cfg) setData((prev) => ({ ...prev, ...cfg }))
    })
    getProjectRepos(project).then((r) => {
      if (r?.repos?.length) setRepos(r.repos)
    })
  }, [])

  const advance = useCallback((from: Step) => {
    setSaveError('')
    setCompleted((prev) => prev.includes(from) ? prev : [...prev, from])
    const idx = STEPS.indexOf(from)
    if (idx < STEPS.length - 1) setStep(STEPS[idx + 1])
  }, [])

  const goBack = useCallback(() => {
    const idx = STEPS.indexOf(step)
    if (idx > 0) setStep(STEPS[idx - 1])
  }, [step])

  const update = useCallback(
    (field: keyof WizardData, value: string) =>
      setData((prev) => ({ ...prev, [field]: value })),
    [],
  )

  const handleSave = async () => {
    if (savingRef.current) return
    savingRef.current = true
    setSaving(true)
    setSaveError('')
    try {
      const primaryUrl = repos.find((r) => r.is_primary)?.repo_url || repos[0]?.repo_url || ''
      const payload = {
        ...Object.fromEntries(Object.entries(data).map(([k, v]) => [k, v || null])),
        project_name: data.project_name,
        repo_url: primaryUrl,
      }
      const configResult = await saveProjectConfig(payload)
      if (configResult?.detail) {
        const msg = Array.isArray(configResult.detail) ? JSON.stringify(configResult.detail) : String(configResult.detail)
        throw new Error(msg)
      }
      // doc_language lives on the project-company write path (ADR-129 PR 13:
      // the only write path) — project-tokens ignores it, so send it there.
      const langResult = await saveProjectCompany({
        project_name: data.project_name,
        doc_language: data.doc_language,
      })
      if (langResult?.detail) {
        const msg = Array.isArray(langResult.detail) ? JSON.stringify(langResult.detail) : String(langResult.detail)
        throw new Error(msg)
      }
      const activeRepos = repos.filter((r) => r.repo_url.trim())
      if (activeRepos.length > 0) {
        const repoResult = await saveProjectRepos(data.project_name, activeRepos)
        if (repoResult?.detail) {
          const msg = Array.isArray(repoResult.detail) ? JSON.stringify(repoResult.detail) : String(repoResult.detail)
          throw new Error(msg)
        }
      }
      await notifyConfigComplete(data.project_name, primaryUrl)
      const scanRes = await triggerScan(data.project_name, 'setup')
      if (!scanRes.ok && scanRes.error) throw new Error(scanRes.error)
      setSaved(true)
      if (scanRes.ok && scanRes.scan_run_id) {
        // ADR-068: jump into the live scan status page
        const q = new URLSearchParams({
          project: data.project_name,
          run: scanRes.scan_run_id,
        })
        window.location.href = `/scan?${q.toString()}`
      } else {
        setTimeout(() => { window.location.href = '/dashboard' }, 2000)
      }
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : typeof e === 'object' ? JSON.stringify(e) : String(e))
    } finally {
      setSaving(false)
      savingRef.current = false
    }
  }

  const handleExampleApp = async () => {
    setExampleLoading(true)
    const exampleData: WizardData = {
      project_name: 'rand-industries',
      company_name: 'Rand Industries Inc.',
      legal_form: 'Inc.',
      contact_email: 'legal@rand-industries.example.com',
      address: '12 Alias Lane',
      zip_code: '10117',
      city: 'Berlin',
      country: 'Germany',
      website_url: 'https://rand-industries.example.com',
      responsible_name: 'Misty Knight',
      responsible_title: 'Managing Director',
      dpo_name: 'Danny Rand',
      dpo_email: 'dpo@rand-industries.example.com',
      doc_language: 'de',
    }
    setData(exampleData)
    const exampleRepos: RepoEntry[] = [{
      repo_url: EXAMPLE_REPO_URL,
      label: 'main',
      is_primary: true,
      github_token: '',
    }]
    setRepos(exampleRepos)

    // Save directly — skip all wizard steps
    try {
      const payload = {
        ...Object.fromEntries(Object.entries(exampleData).map(([k, v]) => [k, v || null])),
        project_name: exampleData.project_name,
        repo_url: EXAMPLE_REPO_URL,
      }
      const configResult = await saveProjectConfig(payload)
      if (configResult?.detail) {
        const msg = Array.isArray(configResult.detail) ? JSON.stringify(configResult.detail) : String(configResult.detail)
        throw new Error(msg)
      }
      const repoResult = await saveProjectRepos('rand-industries', exampleRepos)
      if (repoResult?.detail) {
        const msg = Array.isArray(repoResult.detail) ? JSON.stringify(repoResult.detail) : String(repoResult.detail)
        throw new Error(msg)
      }
      await notifyConfigComplete('rand-industries', EXAMPLE_REPO_URL)
      const scanRes = await triggerScan('rand-industries', 'setup')
      if (!scanRes.ok && scanRes.error) throw new Error(scanRes.error)
      if (scanRes.ok && scanRes.scan_run_id) {
        const q = new URLSearchParams({
          project: 'rand-industries',
          run: scanRes.scan_run_id,
        })
        window.location.href = `/scan?${q.toString()}`
      } else {
        setTimeout(() => { window.location.href = '/dashboard' }, 2000)
      }
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : typeof e === 'object' ? JSON.stringify(e) : String(e))
      setExampleLoading(false)
    }
  }

  if (exampleLoading) {
    return (
      <div style={{ minHeight: '100vh', background: 'var(--bg-base)', display: 'flex' }}>
        <Sidebar />
        <div className="flex items-center justify-center pt-32 flex-1">
          <div className="text-center">
            <div className="text-sm text-[#e2e8f0] mb-2">Setting up Rand Industries... &#9889;</div>
            <div className="text-xs text-[#4a5568]">Saving configuration and triggering first scan</div>
            {saveError && <div className="text-xs text-[#f87171] mt-4">{saveError}</div>}
          </div>
        </div>
      </div>
    )
  }

  return (
    <WizardShell currentStep={step} data={data} completedSteps={completed}>
      {step === 'projekt' && (
        <ProjectStep data={data} update={update} onConfirm={() => advance('projekt')} onExampleApp={handleExampleApp} />
      )}
      {step === 'repos' && (
        <ReposStep repos={repos} setRepos={setRepos} onConfirm={() => advance('repos')} onBack={goBack} />
      )}
      {step === 'company' && (
        <CompanyStep data={data} update={update} onConfirm={() => advance('company')} onBack={goBack} />
      )}
      {step === 'complete' && (
        <CompleteStep data={data} repos={repos} onSave={handleSave} onBack={goBack} saving={saving} saved={saved} error={saveError} />
      )}
    </WizardShell>
  )
}
