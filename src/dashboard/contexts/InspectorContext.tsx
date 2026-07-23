'use client'

import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { sendAssistantMessage, type ProposedAction } from '@/lib/assistant-api'
import { strings } from '@/lib/strings'

// crypto.randomUUID() requires HTTPS; crypto.getRandomValues() works in all contexts.
const genId = (): string => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  const b = new Uint8Array(16)
  crypto.getRandomValues(b)
  b[6] = (b[6] & 0x0f) | 0x40
  b[8] = (b[8] & 0x3f) | 0x80
  return Array.from(b).map((v, i) =>
    ([4, 6, 8, 10].includes(i) ? '-' : '') + v.toString(16).padStart(2, '0')
  ).join('')
}

export type Message = {
  id: string
  role: 'user' | 'assistant'
  text: string
  sources?: string[]
  proposed_actions?: ProposedAction[]
  isError?: boolean
  timestamp: number
}

type InspectorCtx = {
  isOpen: boolean
  messages: Message[]
  isLoading: boolean
  threadId: string | null
  openInspector: () => void
  closeInspector: () => void
  sendMessage: (text: string, displayText?: string) => Promise<void>
}

const InspectorContext = createContext<InspectorCtx | null>(null)

const MAX_MESSAGES = 50

export function InspectorProvider({
  children,
  projectName,
}: {
  children: React.ReactNode
  projectName: string
}) {
  const msgKey    = `lex_messages_${projectName}`
  const threadKey = `lex_thread_${projectName}`

  const [isOpen,    setIsOpen]    = useState(false)
  const [messages,  setMessages]  = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [threadId,  setThreadId]  = useState<string | null>(null)

  useEffect(() => {
    const savedMsgs = localStorage.getItem(msgKey)
    if (savedMsgs) {
      try { setMessages(JSON.parse(savedMsgs)) } catch { /* ignore malformed */ }
    }

    let tid = localStorage.getItem(threadKey)
    if (!tid) {
      tid = genId()
      localStorage.setItem(threadKey, tid)
    }
    setThreadId(tid)

    const pending = localStorage.getItem('lex_proactive_pending')
    if (pending) {
      try {
        const { runId, projectName: pn } = JSON.parse(pending)
        if (pn === projectName && !localStorage.getItem(`lex_proactive_shown_${runId}`)) {
          localStorage.setItem(`lex_proactive_shown_${runId}`, '1')
          localStorage.removeItem('lex_proactive_pending')
          setIsOpen(true)
          const proactiveMsg: Message = {
            id: genId(),
            role: 'assistant',
            text: strings.lex.proactiveText,
            proposed_actions: [{
              action_type: 'ask_followup',
              label: strings.lex.proactiveAction,
              payload: { question: '__gaps__' },
            }],
            timestamp: Date.now(),
          }
          setMessages([proactiveMsg])
          localStorage.setItem(msgKey, JSON.stringify([proactiveMsg]))
        }
      } catch { /* ignore malformed JSON */ }
    }
  }, [projectName, msgKey, threadKey])

  const addMessages = useCallback((msgs: Message[]) => {
    setMessages(prev => {
      const next = [...prev, ...msgs].slice(-MAX_MESSAGES)
      localStorage.setItem(msgKey, JSON.stringify(next))
      return next
    })
  }, [msgKey])

  const sendMessage = useCallback(async (text: string, displayText?: string) => {
    if (!text.trim() || isLoading) return
    setIsLoading(true)

    addMessages([{
      id: genId(),
      role: 'user',
      text: displayText ?? text,
      timestamp: Date.now(),
    }])

    try {
      const resp = await sendAssistantMessage(projectName, text, threadId ?? undefined)

      if (resp.errors?.includes('assistant_unavailable') || resp.response === null) {
        addMessages([{
          id: genId(),
          role: 'assistant',
          text: strings.lex.errorUnavailable,
          isError: true,
          timestamp: Date.now(),
        }])
        return
      }

      addMessages([{
        id: genId(),
        role: 'assistant',
        text: resp.response ?? '',
        sources: resp.sources,
        proposed_actions: resp.proposed_actions,
        timestamp: Date.now(),
      }])
    } catch (err: unknown) {
      const code = err instanceof Error ? err.message : 'unknown'
      const errText =
        code === 'assistant_unavailable' ? strings.lex.errorUnavailable
        : code === 'timeout'            ? strings.lex.errorTimeout
        : code === 'network_error'      ? strings.lex.errorNetwork
        : strings.lex.errorUnknown
      addMessages([{
        id: genId(),
        role: 'assistant',
        text: errText,
        isError: true,
        timestamp: Date.now(),
      }])
    } finally {
      setIsLoading(false)
    }
  }, [isLoading, projectName, threadId, addMessages])

  return (
    <InspectorContext.Provider value={{
      isOpen,
      messages,
      isLoading,
      threadId,
      openInspector:  () => setIsOpen(true),
      closeInspector: () => setIsOpen(false),
      sendMessage,
    }}>
      {children}
    </InspectorContext.Provider>
  )
}

export function useInspector() {
  const ctx = useContext(InspectorContext)
  if (!ctx) throw new Error('useInspector must be used within InspectorProvider')
  return ctx
}
