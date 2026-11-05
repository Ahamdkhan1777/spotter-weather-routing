import { useEffect, useRef, useState } from 'react'
import { api } from '../services/api'
import type { Forecast } from '../types'

export function useForecast(tripId: string | undefined, hour: number) {
  const cache = useRef(new Map<string, Forecast>())
  const [data, setData] = useState<Forecast | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [retry, setRetry] = useState(0)
  useEffect(() => {
    cache.current.clear()
    setData(null)
    setLoading(false)
    setError('')
  }, [tripId])
  useEffect(() => {
    if (!tripId) return
    const key = `${tripId}:${hour}`
    const cached = cache.current.get(key)
    if (cached) { setData(cached); setLoading(false); setError(''); return }
    const controller = new AbortController()
    setLoading(true)
    setError('')
    setData(null) // Never display the preceding hour as if it matched the new slider label.
    const timer = setTimeout(() => {
      api.forecast(tripId, hour, controller.signal).then(forecast => {
        if (controller.signal.aborted) return
        cache.current.set(key, forecast)
        setData(forecast)
      }).catch(error => {
        if (!controller.signal.aborted) setError(error instanceof Error ? error.message : 'Forecast unavailable.')
      }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    }, 160)
    return () => { clearTimeout(timer); controller.abort() }
  }, [tripId, hour, retry])
  return { data, loading, error, retry: () => setRetry(value => value+1) }
}
