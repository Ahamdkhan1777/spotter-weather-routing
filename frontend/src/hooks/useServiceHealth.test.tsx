import { act, cleanup, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { api } from '../services/api'
import type { Health } from '../types'
import { useServiceHealth } from './useServiceHealth'

vi.mock('../services/api', () => ({ api: { health: vi.fn() } }))

const ready: Health = { status: 'ok', routing_configured: true, demo_mode: false }
const unconfigured: Health = { ...ready, routing_configured: false }
const healthRequest = vi.mocked(api.health)

beforeEach(() => {
  vi.useFakeTimers()
  healthRequest.mockReset()
})

afterEach(() => {
  cleanup()
  vi.useRealTimers()
  vi.restoreAllMocks()
})

it('rechecks an unconfigured service after five seconds and stops polling once ready', async () => {
  healthRequest.mockResolvedValueOnce(unconfigured).mockResolvedValue(ready)
  const { result } = renderHook(useServiceHealth)
  await act(async () => {})
  expect(result.current.health?.routing_configured).toBe(false)

  await act(async () => { await vi.advanceTimersByTimeAsync(4999) })
  expect(healthRequest).toHaveBeenCalledTimes(1)
  await act(async () => { await vi.advanceTimersByTimeAsync(1) })
  expect(result.current.health?.routing_configured).toBe(true)
  expect(healthRequest).toHaveBeenCalledTimes(2)

  await act(async () => { await vi.advanceTimersByTimeAsync(15000) })
  expect(healthRequest).toHaveBeenCalledTimes(2)
})

it('allows manual retries after both missing configuration and a failed request', async () => {
  healthRequest.mockResolvedValueOnce(unconfigured)
    .mockRejectedValueOnce(new Error('Routing service unavailable'))
    .mockResolvedValueOnce(ready)
  const { result } = renderHook(useServiceHealth)
  await act(async () => {})
  expect(result.current.health?.routing_configured).toBe(false)

  await act(async () => { result.current.retry() })
  expect(result.current.error).toContain('Routing service unavailable')
  expect(result.current.refreshing).toBe(false)

  await act(async () => { result.current.retry() })
  expect(result.current.health).toEqual(ready)
  expect(result.current.error).toBe('')
  expect(result.current.refreshing).toBe(false)
  expect(healthRequest).toHaveBeenCalledTimes(3)
})

it('refreshes a previously ready service when the browser window regains focus', async () => {
  healthRequest.mockResolvedValueOnce(ready).mockResolvedValueOnce(unconfigured)
  const { result } = renderHook(useServiceHealth)
  await act(async () => {})
  expect(result.current.health?.routing_configured).toBe(true)

  await act(async () => { window.dispatchEvent(new Event('focus')) })
  expect(healthRequest).toHaveBeenCalledTimes(2)
  expect(result.current.health?.routing_configured).toBe(false)
})

it('removes its focus listener and pending retry timer on unmount', async () => {
  const added = vi.spyOn(window, 'addEventListener')
  const removed = vi.spyOn(window, 'removeEventListener')
  healthRequest.mockResolvedValue(unconfigured)
  const { unmount } = renderHook(useServiceHealth)
  await act(async () => {})
  const focusListener = added.mock.calls.find(([event]) => event === 'focus')?.[1]
  expect(focusListener).toBeDefined()
  expect(vi.getTimerCount()).toBeGreaterThan(0)

  unmount()
  expect(removed.mock.calls.some(([event, listener]) => event === 'focus' && listener === focusListener)).toBe(true)
  expect(vi.getTimerCount()).toBe(0)
  await act(async () => {
    window.dispatchEvent(new Event('focus'))
    await vi.advanceTimersByTimeAsync(10000)
  })
  expect(healthRequest).toHaveBeenCalledTimes(1)
})

it('ignores a request that resolves after the hook has unmounted', async () => {
  let resolveHealth!: (health: Health) => void
  healthRequest.mockReturnValueOnce(new Promise<Health>((resolve) => { resolveHealth = resolve }))
  const { result, unmount } = renderHook(useServiceHealth)
  expect(result.current.health).toBeNull()
  expect(result.current.refreshing).toBe(true)
  const beforeUnmount = result.current
  unmount()

  await act(async () => { resolveHealth(unconfigured) })
  expect(result.current).toBe(beforeUnmount)
  expect(vi.getTimerCount()).toBe(0)
  await act(async () => { await vi.advanceTimersByTimeAsync(10000) })
  expect(healthRequest).toHaveBeenCalledTimes(1)
})
