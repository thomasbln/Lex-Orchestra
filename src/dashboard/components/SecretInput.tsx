'use client'
// ADR-083: SecretInput — masked key input with trust hint.
// Shows a "Key set — enter new value to rotate" placeholder when a secret is
// already configured in vault. Never displays the plaintext value — that stays
// in the vault, encrypted at rest.

import { useState } from 'react'

type SecretInputProps = {
  value: string
  onChange: (v: string) => void
  alreadyConfigured?: boolean
  placeholder?: string
  disabled?: boolean
}

export default function SecretInput({
  value,
  onChange,
  alreadyConfigured = false,
  placeholder = 'sk-…',
  disabled = false,
}: SecretInputProps) {
  const [visible, setVisible] = useState(false)

  const effectivePlaceholder = alreadyConfigured && !value
    ? '●●●●●●●● (configured — enter new value to rotate)'
    : placeholder

  return (
    <div style={{ position: 'relative' }}>
      <input
        type={visible ? 'text' : 'password'}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={effectivePlaceholder}
        disabled={disabled}
        autoComplete="off"
        spellCheck={false}
        style={{
          width: '100%',
          background: '#0a0d14',
          border: '1px solid #1e2640',
          borderRadius: '4px',
          padding: '10px 40px 10px 14px',
          fontSize: '13px',
          color: 'var(--text-primary)',
          fontFamily: 'ui-monospace, monospace',
          outline: 'none',
          boxSizing: 'border-box',
          opacity: disabled ? 0.5 : 1,
        }}
        onFocus={e => {
          e.currentTarget.style.boxShadow = '0 0 0 1px #4a8fff, 0 0 8px rgba(74,143,255,0.15)'
        }}
        onBlur={e => {
          e.currentTarget.style.boxShadow = 'none'
        }}
      />
      <button
        type="button"
        onClick={() => setVisible(v => !v)}
        disabled={disabled}
        title={visible ? 'Hide' : 'Show'}
        style={{
          position: 'absolute',
          right: '10px',
          top: '50%',
          transform: 'translateY(-50%)',
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          color: 'var(--text-muted)',
          fontSize: '12px',
          padding: '2px',
        }}
      >
        {visible ? '🙈' : '👁'}
      </button>
      <div style={{
        marginTop: '6px',
        fontSize: '11px',
        color: 'rgba(74,143,255,0.7)',
        fontFamily: 'ui-monospace, monospace',
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
      }}>
        <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
          <path d="M5 1.5C3.07 1.5 1.5 3.07 1.5 5S3.07 8.5 5 8.5 8.5 6.93 8.5 5 6.93 1.5 5 1.5Z"
            stroke="currentColor" strokeWidth="0.8"/>
          <path d="M5 4.5v3M5 3v.5" stroke="currentColor" strokeWidth="0.8" strokeLinecap="round"/>
        </svg>
        {alreadyConfigured
          ? 'Stored in Supabase Vault (AES-256-GCM). Leave blank to keep existing key.'
          : 'Stored encrypted in Supabase Vault — never written to disk as plaintext.'}
      </div>
    </div>
  )
}
