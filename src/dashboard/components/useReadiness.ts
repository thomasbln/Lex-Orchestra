'use client'
import { useEffect, useRef, useState } from 'react'
import { getReadiness, type Readiness } from '../lib/api'

// First-start readiness (status card, sidebar dot, scan-button gates).
// Polls every 10 s ONLY while the system is not ready; a ready system is
// checked once per page load and never polled again. A failed fetch yields
// apiDown — pages keep their existing API-error state as the leading signal.
export function useReadiness(): {
  readiness: Readiness | null
  apiDown: boolean
  loaded: boolean
} {
  const [readiness, setReadiness] = useState<Readiness | null>(null)
  const [apiDown, setApiDown] = useState(false)
  const [loaded, setLoaded] = useState(false)
  const timer = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    let alive = true
    const poll = () =>
      getReadiness()
        .then(r => {
          if (!alive) return
          setReadiness(r)
          setApiDown(false)
          setLoaded(true)
          if (r.ready && timer.current) {
            clearInterval(timer.current)
            timer.current = null
          }
        })
        .catch(() => {
          if (!alive) return
          setApiDown(true)
          setLoaded(true)
        })
    poll()
    timer.current = setInterval(poll, 10_000)
    return () => {
      alive = false
      if (timer.current) clearInterval(timer.current)
    }
  }, [])

  return { readiness, apiDown, loaded }
}
