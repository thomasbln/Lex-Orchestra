'use client'
import { useState, useEffect, Suspense } from 'react'

function CompleteContent() {
  const [project, setProject] = useState('')
  const [repoUrl, setRepoUrl] = useState('')

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    setProject(params.get('project') || '')
    setRepoUrl(params.get('repo') || '')
  }, [])

  return (
    <div className="min-h-screen flex items-center justify-center p-8">
      <div
        className="border border-[#2d2060] rounded-2xl p-10 max-w-lg w-full text-center"
        style={{
          background: '#0d0f1a',
          boxShadow: '0 0 60px rgba(124,58,237,0.1)',
        }}
      >
        <div className="text-4xl mb-4">&#10003;</div>
        <h1 className="text-xl font-semibold text-white mb-2">
          Project configured
        </h1>
        {project && (
          <div className="text-sm text-[#a78bfa] mb-1">{project}</div>
        )}
        {repoUrl && (
          <div className="text-xs text-[#4a5568] truncate mb-6">{repoUrl}</div>
        )}
        {repoUrl && (
          <div className="border border-[#1e2640] rounded-lg p-4 mb-6 text-left">
            <div className="text-xs text-[#4a5568] tracking-widest mb-2">
              NEXT STEP
            </div>
            <p className="text-sm text-[#94a3b8]">
              Start a scan from the dashboard — generated documents appear
              under Docs.
            </p>
          </div>
        )}
        <div className="flex gap-3">
          <a
            href="/setup/"
            className="flex-1 border border-[#2d3748] text-[#94a3b8] hover:border-[#7c3aed] hover:text-white px-4 py-2.5 rounded text-sm tracking-wider transition-all text-center"
          >
            Back to setup
          </a>
          <a
            href="/dashboard/"
            className="flex-1 bg-[#7c3aed] text-white px-4 py-2.5 rounded text-sm tracking-wider hover:bg-[#6d28d9] transition-all text-center"
          >
            View all projects
          </a>
        </div>
      </div>
    </div>
  )
}

export default function SetupCompletePage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center p-8">
          <div className="text-sm text-[#4a5568]">Loading...</div>
        </div>
      }
    >
      <CompleteContent />
    </Suspense>
  )
}
