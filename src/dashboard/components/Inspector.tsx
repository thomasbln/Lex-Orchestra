'use client'

import { useInspector } from '@/contexts/InspectorContext'
import { LexChat } from './LexChat'
import { strings } from '@/lib/strings'

export function Inspector() {
  const { isOpen, openInspector, closeInspector } = useInspector()

  // ADR-129 PR 8: assistant/chat is off for v1.0 — no toggle button, no panel.
  // Reactivation is a build-time flag flip (NEXT_PUBLIC_ASSISTANT_ENABLED=true).
  if (process.env.NEXT_PUBLIC_ASSISTANT_ENABLED !== 'true') return null

  return (
    <>
      <style>{`
        .lex-toggle-btn {
          position: fixed;
          right: ${isOpen ? 320 : 0}px;
          top: 50%;
          transform: translateY(-50%);
          z-index: 40;
          background: var(--bg-surface);
          border: 1px solid var(--border-default);
          border-right: ${isOpen ? 'none' : undefined};
          color: var(--text-muted);
          font-size: 11px;
          font-family: 'JetBrains Mono', monospace;
          padding: 10px 7px;
          cursor: pointer;
          writing-mode: vertical-rl;
          transition: right 200ms ease, background 150ms ease, color 150ms ease;
          letter-spacing: 0.05em;
        }
        .lex-toggle-btn:hover {
          background: var(--bg-elevated);
          color: var(--text-primary);
        }
        .lex-close-btn {
          background: none;
          border: none;
          color: var(--text-muted);
          cursor: pointer;
          font-size: 18px;
          line-height: 1;
          width: 32px;
          height: 32px;
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: 4px;
          transition: background 150ms ease, color 150ms ease;
          flex-shrink: 0;
        }
        .lex-close-btn:hover {
          background: var(--bg-elevated);
          color: var(--text-primary);
        }
      `}</style>

      <button
        className="lex-toggle-btn"
        onClick={isOpen ? closeInspector : openInspector}
        aria-label={isOpen ? strings.lex.ariaClosePanel : strings.lex.ariaOpenPanel}
        style={{ right: isOpen ? 320 : 0 }}
      >
        {isOpen ? strings.lex.toggleClose : strings.lex.toggleOpen}
      </button>

      <div
        style={{
          width: isOpen ? 320 : 0,
          minWidth: isOpen ? 320 : 0,
          overflow: 'hidden',
          transition: 'width 200ms ease, min-width 200ms ease',
          background: 'var(--bg-surface)',
          borderLeft: '1px solid var(--border-default)',
          display: 'flex',
          flexDirection: 'column',
          height: '100vh',
          position: 'sticky',
          top: 0,
          flexShrink: 0,
        }}
      >
        <div style={{
          padding: '10px 12px 10px 16px',
          borderBottom: '1px solid var(--border-default)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexShrink: 0,
          minHeight: 44,
        }}>
          <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)', letterSpacing: '0.08em' }}>
            {strings.lex.panelTitle}
          </span>
          <button
            className="lex-close-btn"
            onClick={closeInspector}
            aria-label={strings.lex.ariaClosePanel}
          >
            ×
          </button>
        </div>

        <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          {isOpen && <LexChat />}
        </div>
      </div>
    </>
  )
}
