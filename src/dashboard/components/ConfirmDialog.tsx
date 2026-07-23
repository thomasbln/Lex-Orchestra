'use client'
import { useEffect, useRef, type ReactNode } from 'react'

// ADR-125: reusable confirmation modal. The codebase had only native confirm()
// before — this gives destructive flows a blast-radius body + a danger button.
// ESC and backdrop click cancel (unless busy); focus lands on Cancel (safe default).

type ConfirmDialogProps = {
  title: string
  body: ReactNode
  confirmLabel: string
  cancelLabel?: string
  danger?: boolean
  busy?: boolean
  error?: string | null
  onConfirm: () => void
  onCancel: () => void
}

export default function ConfirmDialog({
  title,
  body,
  confirmLabel,
  cancelLabel = 'Abbrechen',
  danger = false,
  busy = false,
  error = null,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const cancelRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    cancelRef.current?.focus()
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !busy) onCancel()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [busy, onCancel])

  return (
    <div
      className="modal-scrim"
      role="presentation"
      onClick={() => { if (!busy) onCancel() }}
    >
      <div
        className="modal-card animate-in"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={e => e.stopPropagation()}
      >
        <h2 style={{
          margin: 0,
          fontSize: '18px',
          fontWeight: 700,
          color: 'var(--text-primary)',
          letterSpacing: '-0.01em',
        }}>
          {title}
        </h2>

        <div style={{
          marginTop: '14px',
          fontSize: '13px',
          lineHeight: 1.6,
          color: 'var(--text-secondary)',
        }}>
          {body}
        </div>

        {error && (
          <p role="alert" style={{
            marginTop: '14px',
            marginBottom: 0,
            fontSize: '12px',
            color: 'var(--state-fail)',
            fontFamily: 'ui-monospace, monospace',
          }}>
            {error}
          </p>
        )}

        <div style={{
          display: 'flex',
          justifyContent: 'flex-end',
          gap: '12px',
          marginTop: '24px',
        }}>
          <button
            ref={cancelRef}
            type="button"
            className="btn-secondary"
            onClick={onCancel}
            disabled={busy}
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            className={danger ? 'btn-danger' : 'btn-secondary'}
            onClick={onConfirm}
            disabled={busy}
          >
            {busy ? 'Deleting…' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
