import type { RiskLevel } from './types'

export const RISK_COLORS: Record<RiskLevel, string> = { Low: '#288265', Moderate: '#d6b339', High: '#dc862c', Severe: '#de5353', 'No Travel': '#8e293f', Unknown: '#84939b' }
export const RISK_LEVELS = Object.keys(RISK_COLORS) as RiskLevel[]
export const number = (value: number, digits = 0) => value.toLocaleString(undefined, { maximumFractionDigits: digits })
export const duration = (seconds: number) => `${Math.floor(Math.round(seconds / 60) / 60)}h ${Math.round(seconds / 60) % 60}m`
export const dateTime = (timestamp: string | number) => new Date(typeof timestamp === 'number' ? timestamp * 1000 : timestamp).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', timeZoneName: 'short' })
export const localInput = (date: Date) => new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16)

export function departureISO(local: string): string {
  const date = new Date(local)
  if (!Number.isFinite(date.getTime()) || localInput(date) !== local) throw new Error('This local time does not exist because of a daylight-saving change. Choose another time.')
  // Fall-back repeats are resolved explicitly to the earlier occurrence by the browser.
  return date.toISOString()
}
