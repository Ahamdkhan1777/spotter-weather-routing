import { describe, expect, it } from 'vitest'
import { departureISO, duration, localInput } from './utils'

describe('departure timestamps', () => {
  it('converts a local datetime into an offset-explicit UTC instant', () => {
    const value = localInput(new Date(2026, 10, 5, 14, 30))
    const iso = departureISO(value)
    expect(iso.endsWith('Z')).toBe(true)
    expect(localInput(new Date(iso))).toBe(value)
  })
  it('rejects invalid calendar input', () => {
    expect(() => departureISO('not-a-date')).toThrow()
    expect(() => departureISO('2026-02-30T12:00')).toThrow()
  })
  it('formats elapsed travel time', () => { expect(duration(9300)).toBe('2h 35m'); expect(duration(3599)).toBe('1h 0m') })
})
