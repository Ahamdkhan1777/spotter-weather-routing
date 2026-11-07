import { useState } from 'react'
import { ArrowDownUp, ArrowRight, Clock3, LoaderCircle, Package, Route, X } from 'lucide-react'
import type { TripInput } from '../types'
import { departureISO, localInput } from '../utils'
import { PlaceInput } from './PlaceInput'

export function TripForm({ onSubmit, loading, configured, onCancel }: { onSubmit: (input: TripInput) => void; loading: boolean; configured: boolean; onCancel: () => void }) {
  const [origin, setOrigin] = useState('Dallas, TX')
  const [destination, setDestination] = useState('Austin, TX')
  const [departure, setDeparture] = useState(localInput(new Date(Date.now()+3600000)))
  const [load, setLoad] = useState('35000')
  const [interval, setInterval] = useState(25)
  const [error, setError] = useState('')
  const zone = Intl.DateTimeFormat().resolvedOptions().timeZone
  return <form className="trip-form" onSubmit={event => {
    event.preventDefault(); setError('')
    try {
      const iso = departureISO(departure)
      if (origin.trim().toLowerCase() === destination.trim().toLowerCase()) throw new Error('Choose different origin and destination locations.')
      if (new Date(iso).getTime() < Date.now()) throw new Error('Choose a future departure time.')
      if (!Number.isFinite(Number(load)) || Number(load) <= 0) throw new Error('Enter a positive load weight.')
      onSubmit({ origin: origin.trim(), destination: destination.trim(), departure_at: iso, load_weight_lb: Number(load), interval_miles: interval })
    } catch (error) { setError((error as Error).message) }
  }}>
    <div className="section-eyebrow"><span>01</span> PLAN YOUR TRIP</div>
    <div className="form-heading"><h2>A safer way<br /> to get there.</h2><p>Know what’s ahead before you head out.</p></div>
    <div className="locations">
      <PlaceInput label="Origin" value={origin} onChange={setOrigin} enabled={configured && !loading} />
      <button type="button" className="swap-button" title="Swap origin and destination" aria-label="Swap origin and destination" onClick={() => { setOrigin(destination); setDestination(origin) }}><ArrowDownUp size={14} /></button>
      <PlaceInput label="Destination" value={destination} onChange={setDestination} destination enabled={configured && !loading} />
    </div>
    <label htmlFor="departure">Departure date & time</label>
    <div className="input-icon"><Clock3 size={17} /><input id="departure" type="datetime-local" value={departure} onChange={event => setDeparture(event.target.value)} required /></div>
    <p className="field-hint">Local time · {zone.replaceAll('_', ' ')}</p>
    <label htmlFor="load">Cargo load weight</label>
    <div className="input-icon"><Package size={17} /><input id="load" type="number" min="0.01" max="200000" step="0.01" value={load} onChange={event => setLoad(event.target.value)} required /><span className="input-unit">lb</span></div>
    <fieldset className="interval-field"><legend>Weather checkpoint interval</legend><div className="interval-options">{[10, 25, 50].map(value => <button key={value} type="button" aria-pressed={interval === value} onClick={() => setInterval(value)}>{value} <span>mi</span></button>)}</div><p className="field-hint">Closer checkpoints give a more detailed forecast.</p></fieldset>
    {error && <p className="inline-error" role="alert">{error}</p>}
    <button className="calculate-button" type="submit" disabled={loading}>{loading ? <><LoaderCircle size={18} className="spin" />Analyzing your trip…</> : <><Route size={18} />Find the safest route<ArrowRight size={17} /></>}</button>
    {loading && <button className="text-button cancel-button" type="button" onClick={onCancel}><X size={13} />Cancel request</button>}
    <div className="form-footnote"><ShieldIcon />Arrival-time weather. Load-aware risk.<br /> One clear recommendation.</div>
  </form>
}

function ShieldIcon() { return <svg width="20" height="22" viewBox="0 0 24 26" fill="none" aria-hidden="true"><path d="M12 2 3 6v7c0 5 9 10 9 10s9-5 9-10V6l-9-4Z" stroke="currentColor" strokeWidth="1.5" /><path d="m8 12 3 3 5-6" stroke="currentColor" strokeWidth="1.5" /></svg> }
