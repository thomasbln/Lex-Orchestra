'use client'

import { useRouter } from 'next/navigation'
import { useInspector } from '@/contexts/InspectorContext'
import type { ProposedAction } from '@/lib/assistant-api'
import { strings } from '@/lib/strings'

export function LexProposedActions({ actions }: { actions: ProposedAction[] }) {
  const router = useRouter()
  const { sendMessage } = useInspector()

  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
      <style>{`
        .lex-action-btn {
          background: var(--bg-elevated);
          border: 1px solid var(--border-strong);
          color: var(--text-secondary);
          font-size: 11px;
          padding: 5px 10px;
          min-height: 28px;
          border-radius: 4px;
          cursor: pointer;
          font-family: 'Inter', sans-serif;
          transition: background 150ms ease, border-color 150ms ease, color 150ms ease;
          display: inline-flex;
          align-items: center;
          gap: 4px;
        }
        .lex-action-btn:hover {
          background: var(--bg-surface);
          border-color: var(--accent);
          color: var(--accent);
        }
        .lex-action-btn:disabled {
          opacity: 0.35;
          cursor: not-allowed;
        }
      `}</style>
      {actions.map((action, i) => {
        if (action.action_type === 'navigate') {
          return (
            <button
              key={i}
              className="lex-action-btn"
              onClick={() => router.push(action.payload.url as string)}
            >
              <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true">
                <path d="M1 5h8M5 1l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              {action.label}
            </button>
          )
        }

        if (action.action_type === 'ask_followup') {
          return (
            <button
              key={i}
              className="lex-action-btn"
              onClick={() => sendMessage(action.payload.question as string, action.label)}
            >
              {action.label}
            </button>
          )
        }

        if (action.action_type === 'fill_field' || action.action_type === 'acknowledge') {
          return (
            <button key={i} className="lex-action-btn" disabled>
              {action.label} {strings.lex.phase2Suffix}
            </button>
          )
        }

        return null
      })}
    </div>
  )
}
