'use client'

import { useRef, useEffect, useState } from 'react'
import { useInspector } from '@/contexts/InspectorContext'
import { LexMessageBubble } from './LexMessageBubble'
import { strings } from '@/lib/strings'

const GAPS_DISPLAY = '▦ Show gaps'

export function LexChat() {
  const { messages, isLoading, sendMessage } = useInspector()
  const [text, setText] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  const handleSubmit = () => {
    const trimmed = text.trim()
    if (!trimmed || isLoading) return
    setText('')
    sendMessage(trimmed)
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const sendDisabled = isLoading || !text.trim()

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <style>{`
        .lex-gaps-btn {
          width: 100%;
          height: 36px;
          background: var(--bg-elevated);
          border: 1px solid var(--border-default);
          color: var(--text-secondary);
          font-size: 11px;
          font-family: 'JetBrains Mono', monospace;
          cursor: pointer;
          border-radius: 4px;
          letter-spacing: 0.05em;
          transition: background 150ms ease, border-color 150ms ease, color 150ms ease;
        }
        .lex-gaps-btn:hover:not(:disabled) {
          background: var(--bg-surface);
          border-color: var(--accent);
          color: var(--accent);
        }
        .lex-gaps-btn:disabled { cursor: not-allowed; opacity: 0.4; }
        .lex-send-btn {
          background: var(--bg-elevated);
          border: 1px solid var(--border-default);
          color: var(--text-muted);
          border-radius: 4px;
          width: 44px;
          height: 44px;
          min-width: 44px;
          cursor: pointer;
          font-size: 16px;
          flex-shrink: 0;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: background 150ms ease, border-color 150ms ease, color 150ms ease;
        }
        .lex-send-btn:hover:not(:disabled) {
          background: var(--accent-muted);
          border-color: var(--accent);
          color: var(--accent);
        }
        .lex-send-btn:disabled { cursor: not-allowed; opacity: 0.35; }
        .lex-input {
          flex: 1;
          background: var(--bg-elevated);
          border: 1px solid var(--border-default);
          border-radius: 4px;
          color: var(--text-primary);
          font-size: 12px;
          padding: 10px;
          resize: none;
          font-family: 'Inter', sans-serif;
          outline: none;
          max-height: 80px;
          min-height: 44px;
          line-height: 1.5;
          transition: border-color 150ms ease;
        }
        .lex-input:focus { border-color: var(--accent); }
        .lex-input:disabled { opacity: 0.5; cursor: not-allowed; }
        @keyframes lex-spin {
          to { transform: rotate(360deg); }
        }
        .lex-spinner {
          display: inline-block;
          width: 12px;
          height: 12px;
          border: 1.5px solid var(--border-default);
          border-top-color: var(--accent);
          border-radius: 50%;
          animation: lex-spin 0.7s linear infinite;
          flex-shrink: 0;
        }
      `}</style>

      <div style={{ padding: '8px 12px', borderBottom: '1px solid var(--border-default)', flexShrink: 0 }}>
        <button
          className="lex-gaps-btn"
          onClick={() => sendMessage('__gaps__', GAPS_DISPLAY)}
          disabled={isLoading}
        >
          {strings.lex.showGaps}
        </button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '12px', display: 'flex', flexDirection: 'column' }}>
        {messages.length === 0 ? (
          <p style={{ color: 'var(--text-muted)', fontSize: 12, textAlign: 'center', marginTop: 32, lineHeight: 1.6 }}>
            {strings.lex.placeholder}
          </p>
        ) : (
          messages.map(msg => <LexMessageBubble key={msg.id} message={msg} />)
        )}
        {isLoading && (
          <div style={{
            padding: '8px 10px',
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border-default)',
            borderRadius: 4,
            marginTop: 4,
            color: 'var(--text-muted)',
            fontSize: 12,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}>
            <span className="lex-spinner" />
            {strings.lex.thinking}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div style={{
        padding: '8px 12px',
        borderTop: '1px solid var(--border-default)',
        display: 'flex',
        gap: 8,
        flexShrink: 0,
        alignItems: 'flex-end',
      }}>
        <textarea
          className="lex-input"
          value={text}
          onChange={e => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={1}
          disabled={isLoading}
          placeholder={strings.lex.inputPlaceholder}
        />
        <button
          className="lex-send-btn"
          onClick={handleSubmit}
          disabled={sendDisabled}
          aria-label={strings.lex.sendLabel}
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
            <path d="M1 7h12M7 1l6 6-6 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
      </div>
    </div>
  )
}
