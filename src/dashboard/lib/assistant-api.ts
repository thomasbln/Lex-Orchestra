const API_BASE = typeof window !== 'undefined'
  ? `${window.location.protocol}//${window.location.hostname}:8001`
  : 'http://lex-agent:8001'

export type ProposedAction = {
  action_type: string
  label: string
  payload: Record<string, unknown>
}

export type AssistantResponse = {
  response: string | null
  proposed_actions: ProposedAction[]
  sources: string[]
  intent: string
  thread_id: string
  errors?: string[]
}

export type GapsResponse = {
  gaps: Array<{
    field: string
    priority: number
    gap_reason: string
    fix_url: string
    fix_label: string
  }>
  has_walkthrough_offer: boolean
  gap_count: number
}

// Phase 1: client-side fetch. Phase 2: migrate to Next.js Server Actions for streaming.
export async function sendAssistantMessage(
  projectName: string,
  message: string,
  threadId?: string
): Promise<AssistantResponse> {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 120_000)
  try {
    const res = await fetch(`${API_BASE}/assistant/message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_name: projectName, message, thread_id: threadId }),
      signal: controller.signal,
    })
    if (res.status === 503) throw new Error('assistant_unavailable')
    if (!res.ok) throw new Error('api_error')
    return await res.json()
  } catch (err: unknown) {
    if (err instanceof Error && err.name === 'AbortError') throw new Error('timeout')
    throw err
  } finally {
    clearTimeout(timeout)
  }
}

export async function fetchGaps(projectName: string): Promise<GapsResponse> {
  const res = await fetch(`${API_BASE}/assistant/gaps/${encodeURIComponent(projectName)}`)
  if (!res.ok) throw new Error('api_error')
  return res.json()
}
