// Exported so UI error states can name the exact address they failed to reach
// (F24: a silently swallowed fetch error rendered as "No projects configured").
export const API_BASE = typeof window !== 'undefined'
  ? `${window.location.protocol}//${window.location.hostname}:8001`
  : 'http://lex-agent:8001'

export async function getProjectConfig(projectName: string) {
  const res = await fetch(`${API_BASE}/config/project-tokens/${encodeURIComponent(projectName)}`)
  if (!res.ok) return null
  return res.json()
}

export async function getProjectRepos(projectName: string) {
  const res = await fetch(`${API_BASE}/config/project-repos/${encodeURIComponent(projectName)}`)
  if (!res.ok) return []
  return res.json()
}

export async function saveProjectConfig(data: Record<string, string | null>) {
  const res = await fetch(`${API_BASE}/config/project-tokens`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  const json = await res.json()
  if (!res.ok) console.error('saveProjectConfig error:', res.status, json)
  return json
}

// ADR-076: edit-only update for project_config (no repo_url required).
// Used by /settings, which separates company-data edits from the onboarding
// flow that owns project_tokens.
export async function saveProjectCompany(data: Record<string, string | null>) {
  const res = await fetch(`${API_BASE}/config/project-company`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  const json = await res.json()
  if (!res.ok) console.error('saveProjectCompany error:', res.status, json)
  return json
}

export async function saveInstructingPersons(
  projectName: string,
  instructing_persons: { name: string; title: string }[],
) {
  const res = await fetch(`${API_BASE}/config/instructing_persons`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project_name: projectName, instructing_persons }),
  })
  const json = await res.json()
  if (!res.ok) console.error('saveInstructingPersons error:', res.status, json)
  return json
}

// ── AI deployer config (ADR-124) ────────────────────────────────────────────
// Structure mirrors project_config.ai_config JSONB after migration 023.
// training_data/logging are tri-state booleans: true / false / null|undefined (unset).

export type AiServiceFields = {
  model?: string                      // LLM model (deployer-stated; dropdown + custom)
  purpose?: string                    // UseCase.type (graph-fed dropdown value)
  user_groups?: string                // was nutzergruppen
  usage_limits?: string               // was grenzen
  training_data?: boolean | null      // tri-state
  logging?: boolean | null            // tri-state
}

export type AiProjectLevel = {
  operative_responsible?: string
  tech_responsible?: string
  ai_literacy_measures?: boolean | null   // Art. 4 — tri-state
  ai_literacy_note?: string               // optional free text
}

export type AiConfig = {
  project_level: AiProjectLevel
  per_service: Record<string, AiServiceFields>
}

export type DetectedAiService = { name: string; category: string }

// EU-AI-Act UseCase options for the purpose dropdown (graph-fed, ADR-124).
export type UseCaseOption = {
  type: string
  title_de: string
  risk_level: string          // High | Limited | Minimal | Unacceptable
  article: string | null      // eu_ai_act_article
}

export async function getUseCases(): Promise<UseCaseOption[]> {
  const res = await fetch(`${API_BASE}/usecases`)
  if (!res.ok) return []
  const json = await res.json()
  return Array.isArray(json.usecases) ? json.usecases : []
}

// Curated AI providers (ai_llm + ai_platform) for the "add KI-service" picker (ADR-124 Gate F).
export async function getAiProviders(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/ai-providers`)
  if (!res.ok) return []
  const json = await res.json()
  return Array.isArray(json.providers) ? json.providers : []
}

// Detected AI services for the project (per_service keys) — graph re-query.
export async function getAiServices(projectName: string): Promise<DetectedAiService[]> {
  const res = await fetch(`${API_BASE}/api/ai-services?project=${encodeURIComponent(projectName)}`)
  if (!res.ok) return []
  const json = await res.json()
  return Array.isArray(json.ai_services) ? json.ai_services : []
}

export async function saveProjectAi(projectName: string, aiConfig: AiConfig) {
  const res = await fetch(`${API_BASE}/config/project-ai`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project_name: projectName, ai_config: aiConfig }),
  })
  const json = await res.json()
  if (!res.ok) console.error('saveProjectAi error:', res.status, json)
  return json
}

export async function saveProjectRepos(projectName: string, repos: RepoEntry[]) {
  const res = await fetch(`${API_BASE}/config/project-repos`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project_name: projectName, repos }),
  })
  return res.json()
}

export async function notifyConfigComplete(projectName: string, repoUrl: string) {
  await fetch(`${API_BASE}/notify/config-complete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project_name: projectName, repo_url: repoUrl }),
  }).catch(() => null)
}

export async function triggerScan(
  projectName: string,
  triggeredBy: 'setup' | 'manual' | 'webhook' = 'manual',
): Promise<{ ok: boolean; scan_run_id?: string; error?: string }> {
  const res = await fetch(`${API_BASE}/scan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      project_name: projectName,
      dry_run: false,
      triggered_by: triggeredBy,
    }),
  }).catch(() => null)
  if (!res) return { ok: false, error: 'API unreachable' }
  if (!res.ok) {
    // Surface the server's honest refusal (e.g. 503 "system preparing: llm" —
    // the poll↔click race means a gated click can still reach the API).
    const body = await res.json().catch(() => ({} as { detail?: unknown }))
    const detail = typeof body.detail === 'string' ? body.detail : ''
    const error = detail.startsWith('system preparing')
      ? `System is still preparing (${detail.replace('system preparing: ', '')}) — see the status card on the dashboard. First start downloads the language model once (~10–15 min).`
      : detail || `Scan could not be started (HTTP ${res.status})`
    return { ok: false, error }
  }
  const data = await res.json().catch(() => ({}))
  return { ok: true, scan_run_id: data.scan_run_id || data.run_id }
}

// ── System readiness (first-start status card + scan gate) ──────────────────

export type ReadinessCheck = { ok: boolean; detail: string }
export type Readiness = {
  ready: boolean
  checks: { graph: ReadinessCheck; database: ReadinessCheck; llm: ReadinessCheck }
}

export async function getReadiness(): Promise<Readiness> {
  const res = await fetch(`${API_BASE}/system/readiness`, { cache: 'no-store' })
  if (!res.ok) throw new Error(`readiness ${res.status}`)
  return res.json()
}

// ── ADR-068: scan run status ────────────────────────────────────────────────

export type ScanRunStatus = {
  run_id: string
  scan_run_id: string
  project_name: string
  status: 'running' | 'complete' | 'failed'
  step: 'clone' | 'infra' | 'signals' | 'graph' | 'docgen'
  signals_found: number
  docs_generated: number
  started_at: string | null
  completed_at: string | null
  scanned_at: string | null
  error: string | null
  overall_risk: string | null
  doc_types: string[]
  triggered_by: string | null
}

export async function getScanStatus(runId: string): Promise<ScanRunStatus | null> {
  const res = await fetch(`${API_BASE}/scan/${runId}/status`).catch(() => null)
  if (!res?.ok) return null
  return res.json()
}

export async function extractImpressum(url: string) {
  const res = await fetch(`${API_BASE}/website/extract-impressum`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  })
  return res.json()
}

export type RepoEntry = {
  repo_url: string
  label: string
  github_token: string | null
  is_primary: boolean
}

export type RepoEntryLoaded = {
  repo_url: string
  label: string
  is_primary: boolean
  token_configured: boolean
}

export type ProjectSummary = {
  project_name: string
  company_name: string | null
  repo_url: string | null
}

export async function getProjects(): Promise<ProjectSummary[]> {
  const res = await fetch(`${API_BASE}/config/projects`)
  if (!res.ok) return []
  const data = await res.json()
  return data.projects || []
}

// ── Project deletion (ADR-125) ───────────────────────────────────────────────

export type DeleteCounts = {
  scans: number
  signals: number
  docs: number
  vault_secrets: number
  files: number
}

export type DeletePreview = DeleteCounts & { project_name: string }

export async function getDeletePreview(projectName: string): Promise<DeletePreview> {
  const res = await fetch(
    `${API_BASE}/projects/${encodeURIComponent(projectName)}/delete-preview`,
  )
  if (!res.ok) throw new Error(`delete-preview failed (${res.status})`)
  return res.json()
}

export async function deleteProject(
  projectName: string,
): Promise<{ ok: boolean; deleted: DeleteCounts }> {
  const res = await fetch(
    `${API_BASE}/projects/${encodeURIComponent(projectName)}`,
    { method: 'DELETE' },
  )
  if (!res.ok) throw new Error(`delete failed (${res.status})`)
  return res.json()
}

// ── Schema Explorer ──────────────────────────────────────────────────────────

export async function getGraphSchema() {
  const res = await fetch(`${API_BASE}/graph/schema`)
  if (!res.ok) return { schema: [] }
  return res.json()
}

export async function getNodesByType(nodeType: string, limit = 50) {
  const res = await fetch(`${API_BASE}/graph/nodes/${encodeURIComponent(nodeType)}?limit=${limit}`)
  // error flag instead of a silent empty list — a 400/500 must render as a
  // visible error state, not as "0 nodes" (allowlist-drift finding 2026-07-19).
  if (!res.ok) return { nodes: [], error: true }
  return res.json()
}

export async function getNodeEdges(nodeType: string, nodeId: string) {
  const params = new URLSearchParams({ node_type: nodeType, node_id: nodeId })
  const res = await fetch(`${API_BASE}/graph/node-edges?${params}`)
  if (!res.ok) return { edges: [] }
  return res.json()
}

export async function getEgoGraph(nodeType: string, nodeId: string) {
  const params = new URLSearchParams({ node_type: nodeType, node_id: nodeId })
  const res = await fetch(`${API_BASE}/graph/ego?${params}`)
  if (!res.ok) return { nodes: [], edges: [], center_id: '' }
  return res.json()
}

// ── Scan Signals (ADR-027) ──────────────────────────────────────────────────

export type ScanSignal = {
  id: string
  run_id: string
  signal_type: string
  value: string | null
  confidence: number
  evidence: string[]
  source: string
  created_at: string
  scan_started_at: string | null
}

export type ScanSignalsSummary = {
  last_scan_at: string | null
  signals_count: number
  top_signal_types: string[]
}

export async function getScanSignals(
  project: string,
  limit: number = 50
): Promise<{ signals: ScanSignal[]; count: number }> {
  const params = new URLSearchParams({ project, limit: String(limit) })
  const res = await fetch(`${API_BASE}/api/scan-signals?${params}`)
  if (!res.ok) return { signals: [], count: 0 }
  return res.json()
}

export async function getScanSignalsSummary(
  project: string
): Promise<ScanSignalsSummary> {
  const res = await fetch(`${API_BASE}/api/scan-signals/summary?project=${encodeURIComponent(project)}`)
  if (!res.ok) return { last_scan_at: null, signals_count: 0, top_signal_types: [] }
  return res.json()
}

// ── Logs (ADR-045) ──────────────────────────────────────────────────────────

export type LogEvent = {
  ts: string
  run_id: string
  event: string
  [key: string]: unknown
}

export type LogsResponse = {
  events: LogEvent[]
  total: number
  run_ids: string[]
  // Part 3 follow-up: same scan-select metadata as /docs (shared backend helper).
  runs?: RunMeta[]
}

export async function getLogs(
  filter: string = 'all',
  runId: string = '',
  lines: number = 100
): Promise<LogsResponse> {
  const params = new URLSearchParams({ filter, lines: String(lines) })
  if (runId) params.set('run_id', runId)
  const res = await fetch(`${API_BASE}/logs?${params}`)
  if (!res.ok) return { events: [], total: 0, run_ids: [] }
  return res.json()
}

export interface DocMeta {
  filename: string
  doc_type: string
  run_id: string
  created_at: number
  size_bytes: number
  pdf_filename: string | null
  // ADR-111: provenance logbook companion, present only for AVV/VVT/SCC.
  logbook_filename: string | null
  // ADR-112: per-run graph retrieval trace (same value for all docs of a run).
  retrieval_trace_filename: string | null
  // ADR-127 P5d: full run UUID (run_id above is the 8-char display label). Null when
  // the file has no generated_docs row (e.g. scan_report). Editor/edit-link use this.
  run_id_full?: string | null
}

// Scan-select metadata (additive, 2026-07-19): one entry per file-run that exists
// in scan_results, newest first. A file-run MISSING from a non-empty list means
// its project was deleted; an empty/absent list means "no metadata" (DB down).
export interface RunMeta {
  run_id: string            // 8-char display id (matches DocMeta.run_id)
  run_id_full: string       // full UUID
  project_name: string | null
  scan_time: string | null  // ISO, COALESCE(started_at, completed_at)
  status: string | null     // 'complete' | 'failed' | ...
}

export interface DocsResponse {
  docs: DocMeta[]
  total: number
  runs?: RunMeta[]
  // ADR-127 P4.5/P5d: FULL run UUIDs that are editable = latest run with an
  // owner_measures snapshot per project. Match against DocMeta.run_id_full (not the
  // 8-char run_id). Absent/empty → no run is editable.
  editable_run_ids?: string[]
}

// Direct PDF download URL (FileResponse serves it as an attachment).
export function getPdfDownloadUrl(pdfFilename: string): string {
  return `${API_BASE}/docs/pdf/${encodeURIComponent(pdfFilename)}`
}

// ADR-111: direct provenance-logbook download URL (JSON attachment).
export function getLogbookDownloadUrl(logbookFilename: string): string {
  return `${API_BASE}/docs/logbook/${encodeURIComponent(logbookFilename)}`
}

// ADR-112: direct per-run graph retrieval-trace download URL (JSON attachment).
export function getRetrievalTraceDownloadUrl(traceFilename: string): string {
  return `${API_BASE}/docs/retrieval-trace/${encodeURIComponent(traceFilename)}`
}

export async function getDocs(runId?: string): Promise<DocsResponse> {
  const params = new URLSearchParams()
  if (runId) params.set('run_id', runId)
  const qs = params.toString()
  const res = await fetch(`${API_BASE}/docs${qs ? `?${qs}` : ''}`)
  if (!res.ok) return { docs: [], total: 0 }
  return res.json()
}

export async function getDocContent(filename: string): Promise<string> {
  const res = await fetch(`${API_BASE}/docs/file/${encodeURIComponent(filename)}`)
  if (!res.ok) return ''
  const data = await res.json()
  return data.content ?? ''
}

// ── ADR-127 Phase 5: owner-measure editor client (against P5a/P4.6 backend) ──

export interface MeasureLang {
  framework: string
  title: string
  default_text: string
  text: string | null      // owner edit; null = unedited (default_text renders)
  edited_flag: boolean
  source: string           // 'lex-llm-draft' | 'owner'
}

export interface MeasureEntry {
  de: MeasureLang | null
  en: MeasureLang | null   // null where the control has no EN measure (e.g. OWASP)
  deleted: boolean         // lang-agnostic soft-delete
}

export interface MeasuresResponse {
  run_id: string
  project_name: string
  measures: Record<string, MeasureEntry>   // control_id → entry
}

export type MeasureAction = 'edit' | 'reset' | 'deactivate' | 'reactivate' | 'add' | 'delete'

// P5a: read the owner-measure overlay for a run (editor source). Throws on non-OK.
export async function getMeasures(runId: string): Promise<MeasuresResponse> {
  const res = await fetch(`${API_BASE}/scan/${encodeURIComponent(runId)}/measures`)
  if (!res.ok) throw new Error(`getMeasures failed: ${res.status}`)
  return res.json()
}

// P5a/PR5e-5: apply one owner action. `text`/`title` for edit/add; `controlId`
// is null for action='add' (the server generates the custom id and returns it).
export async function saveMeasure(
  runId: string,
  controlId: string | null,
  lang: string,
  action: MeasureAction,
  text?: string,
  title?: string,
  framework?: string,
): Promise<{ ok: boolean; updated?: number; control_id?: string }> {
  const res = await fetch(`${API_BASE}/scan/${encodeURIComponent(runId)}/measures`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ control_id: controlId, lang, action, text, title, framework }),
  })
  if (!res.ok) throw new Error(`saveMeasure (${action}) failed: ${res.status}`)
  return res.json()
}

// P4.6: re-render a run's documents without a re-scan (owner overlay applies in place).
export async function rerenderRun(
  runId: string,
): Promise<{ ok: boolean; rerendered?: number; doc_types?: string[] }> {
  const res = await fetch(`${API_BASE}/scan/${encodeURIComponent(runId)}/rerender`, {
    method: 'POST',
  })
  if (!res.ok) throw new Error(`rerenderRun failed: ${res.status}`)
  return res.json()
}

// ── ADR-076: Project Setup (Layer 2 questionnaire) ──────────────────────────

export type RetentionPolicyIn = {
  category: string
  duration_days: number | null
  duration_raw: string
  source?: 'code' | 'setup' | 'firecrawl'
}

export type ProjectSetupPayload = {
  on_prem: boolean
  hosting_provider: string | null
  hosting_region: string | null
  retention_policies: RetentionPolicyIn[]
  created_by?: string | null
}

export type ProjectSetupResponse = {
  setup: {
    project_name: string
    current_revision_id: string | null
    on_prem: boolean
    hosting_provider: string | null
    hosting_region: string | null
    updated_at: string | null
  } | null
  revisions: { id: string; created_at: string | null; created_by: string | null }[]
  retention_policies: (RetentionPolicyIn & { extracted_from: string | null })[]
}

export async function getProjectSetup(
  projectName: string
): Promise<ProjectSetupResponse> {
  const res = await fetch(
    `${API_BASE}/projects/${encodeURIComponent(projectName)}/setup`
  )
  if (!res.ok) return { setup: null, revisions: [], retention_policies: [] }
  return res.json()
}

export async function saveProjectSetup(
  projectName: string,
  payload: ProjectSetupPayload
): Promise<{ project_name: string; revision_id: string } | { detail: string }> {
  const res = await fetch(
    `${API_BASE}/projects/${encodeURIComponent(projectName)}/setup`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }
  )
  const json = await res.json()
  if (!res.ok) console.error('saveProjectSetup error:', res.status, json)
  return json
}

// ── ADR-082: Integration Catalog ────────────────────────────────────────────

export type CatalogIntegration = {
  name: string
  subcategory: string | null
  capabilities: string[]
  required_credentials: string[]
  pricing_tier: string | null
  documentation_url: string | null
  region: string | null
  requires_scc: boolean
}

export type ProjectIntegration = {
  integration: string
  enabled: boolean
  config: Record<string, unknown>
  connected_at: string | null
  last_sync_at: string | null
  last_error: string | null
  has_credentials: boolean
}

export async function getIntegrationCatalog(): Promise<CatalogIntegration[]> {
  const res = await fetch(`${API_BASE}/integrations/catalog`).catch(() => null)
  if (!res?.ok) return []
  const data = await res.json()
  return data.catalog || []
}

export async function getProjectIntegrations(
  projectName: string
): Promise<ProjectIntegration[]> {
  const res = await fetch(
    `${API_BASE}/projects/${encodeURIComponent(projectName)}/integrations`
  ).catch(() => null)
  if (!res?.ok) return []
  const data = await res.json()
  return data.integrations || []
}

export async function upsertProjectIntegration(
  projectName: string,
  integration: string,
  apiKey?: string
): Promise<{ ok: boolean }> {
  const res = await fetch(
    `${API_BASE}/projects/${encodeURIComponent(projectName)}/integrations/${encodeURIComponent(integration)}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ api_key: apiKey || null }),
    }
  ).catch(() => null)
  if (!res?.ok) return { ok: false }
  return res.json()
}

export async function deleteProjectIntegration(
  projectName: string,
  integration: string
): Promise<{ ok: boolean }> {
  const res = await fetch(
    `${API_BASE}/projects/${encodeURIComponent(projectName)}/integrations/${encodeURIComponent(integration)}`,
    { method: 'DELETE' }
  ).catch(() => null)
  if (!res?.ok) return { ok: false }
  return res.json()
}
