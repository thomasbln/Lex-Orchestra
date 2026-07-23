module.exports = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      colors: {
        bg: {
          base:     '#0a0e1a',
          surface:  '#0d1220',
          elevated: '#131929',
          overlay:  '#1a2236',
        },
        accent: {
          DEFAULT: '#4a8fff',
          hover:   '#6aa3ff',
          muted:   'rgba(74,143,255,0.12)',
        },
        state: {
          pass: '#4ade80',
          warn: '#f59e0b',
          fail: '#f87171',
          info: '#60a5fa',
        },
        text: {
          primary:   '#e2e8f0',
          secondary: '#94a3b8',
          muted:     '#64748b',
        },
        border: {
          default: 'rgba(255,255,255,0.07)',
          strong:  'rgba(255,255,255,0.14)',
        },
      },
    },
  },
  plugins: [],
}
