'use client'

import { Suspense, useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { getScanStatus, type ScanRunStatus } from '@/lib/api'

type StepKey = 'clone' | 'infra' | 'signals' | 'graph' | 'docgen'

const STEPS: { key: StepKey; label: string }[] = [
  { key: 'clone',   label: 'Repository cloned' },
  { key: 'infra',   label: 'Tech stack identified' },
  { key: 'signals', label: 'Services detected' },
  { key: 'graph',   label: 'Compliance requirements mapped' },
  { key: 'docgen',  label: 'Documents generated' },
]

export default function ScanStatusPage() {
  return (
    <Suspense fallback={<div style={{ minHeight: '100vh', background: 'var(--bg-base)' }} />}>
      <ScanStatusContent />
    </Suspense>
  )
}

function ScanStatusContent() {
  const searchParams = useSearchParams()
  const projectId = searchParams.get('project') || ''
  const runId = searchParams.get('run') || ''
  const [scan, setScan] = useState<ScanRunStatus | null>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [autoCountdown, setAutoCountdown] = useState(10)
  const [autoCancelled, setAutoCancelled] = useState(false)

  useEffect(() => {
    if (!runId) return
    let cancelled = false

    const poll = async () => {
      const data = await getScanStatus(runId)
      if (cancelled) return

      if (!data) {
        timerRef.current = setTimeout(poll, 3000)
        return
      }
      setScan(data)

      if (data.status === 'complete') {
        if (!localStorage.getItem(`lex_proactive_shown_${runId}`)) {
          localStorage.setItem('lex_proactive_pending', JSON.stringify({ runId, projectName: projectId }))
        }
      }

      if (data.status === 'complete' || data.status === 'failed') return

      timerRef.current = setTimeout(poll, 2000)
    }

    poll()

    return () => {
      cancelled = true
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [runId])

  // ADR-068: auto-redirect countdown after 'complete' — cancelable
  useEffect(() => {
    if (scan?.status !== 'complete' || autoCancelled) return
    if (autoCountdown <= 0) {
      window.location.href = `/docs?run_id=${runId}`
      return
    }
    const t = setTimeout(() => setAutoCountdown((n) => n - 1), 1000)
    return () => clearTimeout(t)
  }, [scan?.status, autoCountdown, autoCancelled, runId])

  const currentStepIndex = STEPS.findIndex((s) => s.key === scan?.step)
  const effectiveIndex = currentStepIndex === -1 ? 0 : currentStepIndex

  const getStepState = (index: number): 'done' | 'running' | 'pending' => {
    if (!scan) return 'pending'
    if (scan.status === 'complete') return 'done'
    if (index < effectiveIndex) return 'done'
    if (index === effectiveIndex) return scan.status === 'failed' ? 'pending' : 'running'
    return 'pending'
  }

  const headline =
    scan?.status === 'complete' ? 'Scan complete'
    : scan?.status === 'failed' ? 'Scan failed'
    : 'Scan running'

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-base)' }}>
      <div style={{ maxWidth: 640, margin: '0 auto', padding: '48px 24px' }}>
        <div style={{ marginBottom: 32 }}>
          <div style={{
            fontFamily: 'var(--font-mono, ui-monospace)',
            fontSize: 11,
            letterSpacing: '0.15em',
            color: 'var(--text-muted)',
            marginBottom: 8,
            textTransform: 'uppercase',
          }}>
            {projectId}
          </div>
          <h1 style={{
            fontSize: 22,
            fontWeight: 700,
            color: 'var(--text-primary)',
            marginBottom: 4,
          }}>
            {headline}
          </h1>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
            {scan?.status === 'complete'
              ? `${scan.signals_found} ${scan.signals_found === 1 ? 'service' : 'services'} · ${scan.docs_generated} ${scan.docs_generated === 1 ? 'document' : 'documents'}`
              : scan?.status === 'failed'
              ? scan.error ?? 'Unknown error'
              : 'Your repository is being analysed.'}
          </p>
        </div>

        {scan?.status === 'running' && (
          <div style={{
            display: 'flex',
            alignItems: 'flex-start',
            gap: 12,
            padding: '14px 18px',
            marginBottom: 28,
            background: 'var(--state-info-muted)',
            border: '0.5px solid var(--border-accent)',
            borderRadius: 4,
            fontSize: 13,
            color: 'var(--text-primary)',
          }}>
            <span className="scan-pulse" style={{
              width: 8,
              height: 8,
              marginTop: 5,
              borderRadius: '50%',
              background: 'var(--state-info)',
              flexShrink: 0,
            }} aria-hidden />
            <span>
              <strong style={{ color: 'var(--text-primary)' }}>Your repository is being scanned.</strong>{' '}
              <span style={{ color: 'var(--text-secondary)' }}>
                Compliance documents are being generated.
              </span>
            </span>
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {STEPS.map((step, i) => {
            const state = getStepState(i)
            const extra =
              step.key === 'signals' && state !== 'pending' && scan
                ? `${scan.signals_found} ${scan.signals_found === 1 ? 'service' : 'services'}`
                : step.key === 'docgen' && state === 'done' && scan
                ? `${scan.docs_generated} ${scan.docs_generated === 1 ? 'document' : 'documents'}`
                : null
            return (
              <div
                key={step.key}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 14,
                  padding: '12px 16px',
                  background: 'var(--bg-surface)',
                  border: '0.5px solid var(--border-default)',
                  borderRadius: 4,
                  fontSize: 13,
                  color:
                    state === 'pending' ? 'var(--text-muted)'
                    : state === 'running' ? 'var(--text-primary)'
                    : 'var(--text-primary)',
                  opacity: state === 'pending' ? 0.55 : 1,
                  fontWeight: state === 'running' ? 500 : 400,
                  transition: 'opacity 200ms ease',
                }}
              >
                <StepIcon state={state} />
                <span style={{ flex: 1 }}>{step.label}</span>
                {extra && (
                  <span style={{
                    fontFamily: 'var(--font-mono, ui-monospace)',
                    fontSize: 11,
                    color: 'var(--text-muted)',
                  }}>
                    {extra}
                  </span>
                )}
              </div>
            )
          })}
        </div>

        {scan?.status === 'running' && (
          <p style={{
            marginTop: 32,
            fontSize: 12,
            color: 'var(--text-muted)',
            textAlign: 'center',
          }}>
            You can leave this tab — the scan keeps running; documents appear under Docs when it completes.
          </p>
        )}

        {scan?.status === 'complete' && (
          <div style={{ marginTop: 40, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14 }}>
            <a
              href={`/docs?run_id=${runId}`}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 10,
                padding: '11px 22px',
                background: 'var(--accent)',
                color: '#ffffff',
                fontSize: 13,
                fontWeight: 500,
                letterSpacing: '0.02em',
                borderRadius: 4,
                textDecoration: 'none',
                transition: 'background 150ms ease',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--accent-hover)')}
              onMouseLeave={(e) => (e.currentTarget.style.background = 'var(--accent)')}
            >
              Open documents
              <span style={{ fontSize: 14, lineHeight: 1 }}>→</span>
            </a>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', display: 'flex', gap: 8 }}>
              {autoCancelled ? (
                <span>Auto-redirect cancelled</span>
              ) : (
                <>
                  <span>Auto-redirect in {autoCountdown}s</span>
                  <span aria-hidden>·</span>
                  <button
                    onClick={() => setAutoCancelled(true)}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      padding: 0,
                      color: 'var(--accent)',
                      fontSize: 11,
                      cursor: 'pointer',
                      fontFamily: 'inherit',
                    }}
                  >
                    cancel
                  </button>
                </>
              )}
            </div>
          </div>
        )}

        {scan?.status === 'failed' && (
          <div style={{ marginTop: 32, display: 'flex', justifyContent: 'center' }}>
            <a
              href="/dashboard"
              style={{
                fontSize: 12,
                color: 'var(--accent)',
                textDecoration: 'none',
                borderBottom: '0.5px solid var(--border-accent)',
                paddingBottom: 1,
              }}
            >
              Back to project
            </a>
          </div>
        )}
      </div>

    </div>
  )
}

function StepIcon({ state }: { state: 'done' | 'running' | 'pending' }) {
  const size = 16
  if (state === 'done') {
    return (
      <span style={{
        width: size, height: size, display: 'inline-flex',
        alignItems: 'center', justifyContent: 'center',
        color: 'var(--state-pass)', fontFamily: 'var(--font-mono, ui-monospace)',
        fontSize: 13, fontWeight: 600,
      }} aria-hidden>
        ✓
      </span>
    )
  }
  if (state === 'running') {
    return (
      <span
        aria-hidden
        className="scan-spin"
        style={{
          width: size, height: size, display: 'inline-block',
          border: '1.5px solid var(--state-info-muted)',
          borderTopColor: 'var(--state-info)',
          borderRadius: '50%',
        }}
      />
    )
  }
  return (
    <span
      aria-hidden
      style={{
        width: size, height: size,
        borderRadius: '50%',
        border: '1px solid var(--border-default)',
        display: 'inline-block',
      }}
    />
  )
}
