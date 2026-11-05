import { useCallback, useEffect, useState } from 'react'
import { api } from '../services/api'
import type { Health } from '../types'

export function useServiceHealth() {
  const [health, setHealth] = useState<Health | null>(null)
  const [error, setError] = useState('')
  const [refreshing, setRefreshing] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const retry = useCallback(() => setAttempt(value => value + 1), [])

  useEffect(() => {
    let active = true
    let pending = false
    let timer: ReturnType<typeof setTimeout> | undefined

    async function refresh() {
      if (!active || pending) return
      clearTimeout(timer)
      pending = true
      setRefreshing(true)
      let ready = false
      try {
        const result = await api.health()
        if (!active) return
        ready = result.routing_configured
        setHealth(result)
        setError('')
      } catch (error) {
        if (!active) return
        setError(error instanceof Error ? error.message : 'Cannot reach the routing service.')
      } finally {
        pending = false
        if (active) {
          setRefreshing(false)
          // Recover automatically after credentials are saved or Django restarts.
          if (!ready) timer = setTimeout(refresh, 5000)
        }
      }
    }

    function onVisible() {
      if (document.visibilityState === 'visible') void refresh()
    }

    void refresh()
    window.addEventListener('focus', refresh)
    window.addEventListener('online', refresh)
    window.addEventListener('pageshow', refresh)
    document.addEventListener('visibilitychange', onVisible)

    return () => {
      active = false
      clearTimeout(timer)
      window.removeEventListener('focus', refresh)
      window.removeEventListener('online', refresh)
      window.removeEventListener('pageshow', refresh)
      document.removeEventListener('visibilitychange', onVisible)
    }
  }, [attempt])

  return { health, error, refreshing, retry }
}
