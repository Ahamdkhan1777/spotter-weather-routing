import { afterEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { TripForm } from './TripForm'

afterEach(cleanup)

it('submits an aware departure, selected interval, and numeric cargo weight', () => {
  const submit = vi.fn()
  render(<TripForm onSubmit={submit} loading={false} configured={false} onCancel={() => {}} />)
  fireEvent.click(screen.getByRole('button', { name: '50 mi' }))
  fireEvent.click(screen.getByRole('button', { name: /Find the safest route/ }))
  expect(submit).toHaveBeenCalledWith(expect.objectContaining({ origin: 'Dallas, TX', destination: 'Austin, TX', interval_miles: 50, load_weight_lb: 35000, departure_at: expect.stringMatching(/Z$/) }))
})

it('rejects identical locations before sending a request', () => {
  const submit = vi.fn()
  render(<TripForm onSubmit={submit} loading={false} configured={false} onCancel={() => {}} />)
  fireEvent.change(screen.getByLabelText('Destination'), { target: { value: 'Dallas, TX' } })
  fireEvent.click(screen.getByRole('button', { name: /Find the safest route/ }))
  expect(submit).not.toHaveBeenCalled()
  expect(screen.getByRole('alert').textContent).toContain('different origin')
})

it('swaps locations and prevents duplicate submissions while loading', () => {
  const { rerender } = render(<TripForm onSubmit={() => {}} loading={false} configured={false} onCancel={() => {}} />)
  fireEvent.click(screen.getByRole('button', { name: 'Swap origin and destination' }))
  expect((screen.getByLabelText('Origin') as HTMLInputElement).value).toBe('Austin, TX')
  rerender(<TripForm onSubmit={() => {}} loading={true} configured={false} onCancel={() => {}} />)
  expect((screen.getByRole('button', { name: /Analyzing/ }) as HTMLButtonElement).disabled).toBe(true)
})
