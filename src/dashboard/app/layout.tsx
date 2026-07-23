import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Lex-Orchestra — Compliance Terminal',
  description: 'Sovereign Compliance Automation',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="de">
      <body>{children}</body>
    </html>
  )
}
