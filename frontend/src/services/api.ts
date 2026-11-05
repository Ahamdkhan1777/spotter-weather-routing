import type { Forecast, Health, Place, Trip, TripInput } from '../types'

const base = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const timeout = AbortSignal.timeout(120000)
  const signal = options.signal ? AbortSignal.any([options.signal, timeout]) : timeout
  let response: Response
  try {
    response = await fetch(`${base}/api${path}`, { ...options, signal, headers: { 'Content-Type': 'application/json', ...options.headers } })
  } catch (error) {
    if (options.signal?.aborted) throw error
    throw new Error('Cannot reach the routing service. Check that the Django backend is running, then retry.')
  }
  let data: unknown
  try { data = await response.json() } catch { throw new Error('The service returned an invalid response. Please retry.') }
  if (!response.ok) {
    const body = data as Record<string, unknown>
    const structured = body.error as { message?: string } | undefined
    const details = Object.entries(body).map(([key, value]) => `${key.replaceAll('_', ' ')}: ${Array.isArray(value) ? value.join(' ') : String(value)}`).join('; ')
    throw new Error(structured?.message || details || 'Request failed. Please retry.')
  }
  return data as T
}

export const api = {
  health: () => request<Health>('/health/'),
  places: (query: string, signal: AbortSignal) => request<{ places: Place[] }>(`/places/?q=${encodeURIComponent(query)}`, { signal }),
  calculate: (input: TripInput, signal: AbortSignal) => request<Trip>('/routes/calculate/', { method: 'POST', body: JSON.stringify(input), signal }),
  forecast: (id: string, hour: number, signal: AbortSignal) => request<Forecast>(`/trips/${id}/forecast/?hour=${hour}`, { signal }),
}
