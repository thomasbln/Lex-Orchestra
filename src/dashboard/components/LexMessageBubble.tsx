'use client'

import { useInspector } from '@/contexts/InspectorContext'
import { LexProposedActions } from './LexProposedActions'
import type { Message } from '@/contexts/InspectorContext'

export function LexMessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user'
  const { messages, sendMessage, isLoading } = useInspector()

  const handleRetry = () => {
    const lastUser = [...messages].reverse().find(m => m.role === 'user')
    if (lastUser) sendMessage(lastUser.text)
  }

  const bubbleStyle: React.CSSProperties = {
    padding: '8px 10px',
    borderRadius: 4,
    fontSize: 12,
    lineHeight: 1.5,
    marginBottom: 6,
    maxWidth: '90%',
    alignSelf: isUser ? 'flex-end' : 'flex-start',
    ...(isUser ? {
      background: 'var(--accent-muted)',
      border: '1px solid var(--border-accent)',
      color: 'var(--text-primary)',
    } : message.isError ? {
      background: 'var(--state-fail-muted)',
      border: '1px solid var(--state-fail)',
      color: 'var(--state-fail)',
    } : {
      background: 'var(--bg-elevated)',
      border: '1px solid var(--border-default)',
      color: 'var(--text-primary)',
    }),
  }

  return (
    <>
      <style>{`
        .lex-retry-btn {
          background: none;
          border: 1px solid var(--state-fail);
          color: var(--state-fail);
          font-size: 11px;
          padding: 4px 10px;
          min-height: 28px;
          border-radius: 4px;
          cursor: pointer;
          font-family: 'Inter', sans-serif;
          display: inline-flex;
          align-items: center;
          gap: 4px;
          align-self: flex-start;
          margin-bottom: 8px;
          opacity: 0.85;
          transition: opacity 150ms ease, background 150ms ease;
        }
        .lex-retry-btn:hover:not(:disabled) {
          opacity: 1;
          background: var(--state-fail-muted);
        }
        .lex-retry-btn:disabled { opacity: 0.4; cursor: not-allowed; }
      `}</style>

      <div style={{ display: 'flex', flexDirection: 'column' }}>
        <div style={bubbleStyle}>
          <span style={{ whiteSpace: 'pre-wrap' }}>{message.text}</span>
        </div>

        {message.isError && (
          <button
            className="lex-retry-btn"
            onClick={handleRetry}
            disabled={isLoading}
          >
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true">
              <path d="M1 5a4 4 0 1 0 1.2-2.8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
              <path d="M1 1v3h3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            Retry
          </button>
        )}

        {!isUser && message.sources && message.sources.length > 0 && (
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4, paddingLeft: 2 }}>
            {message.sources.slice(0, 3).join(' · ')}
          </div>
        )}

        {!isUser && message.proposed_actions && message.proposed_actions.length > 0 && (
          <LexProposedActions actions={message.proposed_actions} />
        )}
      </div>
    </>
  )
}
