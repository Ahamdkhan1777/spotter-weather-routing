import { useEffect, useId, useRef, useState } from 'react'
import { MapPin, LocateFixed } from 'lucide-react'
import { api } from '../services/api'
import type { Place } from '../types'

export function PlaceInput({ label, value, onChange, destination, enabled }: { label: string; value: string; onChange: (value: string) => void; destination?: boolean; enabled: boolean }) {
  const id = useId()
  const [places, setPlaces] = useState<Place[]>([])
  const [focused, setFocused] = useState(false)
  const [status, setStatus] = useState('')
  const chosen = useRef(value)
  useEffect(() => {
    if (!enabled || !focused || value.length < 3 || value === chosen.current) { setPlaces([]); return }
    const controller = new AbortController()
    const timer = setTimeout(() => {
      setStatus('Searching locations…')
      api.places(value, controller.signal).then(result => { setPlaces(result.places); setStatus(result.places.length ? '' : 'No matching locations. Try a full address.') })
        .catch(error => { if (!controller.signal.aborted) { setPlaces([]); setStatus(error.message) } })
    }, 450)
    return () => { clearTimeout(timer); controller.abort() }
  }, [value, enabled, focused])
  const Icon = destination ? MapPin : LocateFixed
  return <div className="place-field">
    <label htmlFor={id}>{label}</label>
    <div className="input-icon"><Icon size={17} /><input id={id} value={value} placeholder={destination ? 'City or destination address' : 'City or starting address'} onChange={event => onChange(event.target.value)} onFocus={() => setFocused(true)} onBlur={() => { setFocused(false); setStatus('') }} required minLength={2} maxLength={200} autoComplete="off" aria-describedby={status ? `${id}-status` : undefined} /></div>
    {focused && places.length > 0 && <ul className="suggestions" aria-label={`${label} suggestions`}>{places.map(place => <li key={place.label}><button type="button" onMouseDown={event => event.preventDefault()} onClick={() => { chosen.current = place.label; onChange(place.label); setPlaces([]); setFocused(false) }}><MapPin size={14} />{place.label}</button></li>)}</ul>}
    {focused && status && <small id={`${id}-status`} className="field-hint">{status}</small>}
  </div>
}
