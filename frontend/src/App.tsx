import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import { ArrowRight, Check, ChevronDown, ChevronUp, CircleHelp, CloudSun, Info, LoaderCircle, Moon, Route as RouteIcon, ShieldCheck, Sun, TriangleAlert, Truck } from 'lucide-react'
import { TripForm } from './components/TripForm'
import { RouteCard } from './components/RouteCard'
import { CheckpointDetails } from './components/CheckpointDetails'
import { RiskBadge } from './components/RiskBadge'
import { useForecast } from './hooks/useForecast'
import { useServiceHealth } from './hooks/useServiceHealth'
import { useTheme } from './hooks/useTheme'
import { api } from './services/api'
import type { Trip, TripInput } from './types'
import { dateTime, duration, number } from './utils'

const MapPanel = lazy(() => import('./components/MapPanel'))

export default function App() {
  const { theme, setTheme } = useTheme()
  const { health, error: healthError, refreshing: healthRefreshing, retry: retryHealth } = useServiceHealth()
  const [trip, setTrip] = useState<Trip | null>(null)
  const [selectedRoute, setSelectedRoute] = useState<string | null>(null)
  const [checkpointId, setCheckpointId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [hour, setHour] = useState(0)
  const [heatmap, setHeatmap] = useState(true)
  const [showNotes, setShowNotes] = useState(false)
  const [showRules, setShowRules] = useState(false)
  const [mapVisible, setMapVisible] = useState(false)
  const request = useRef<AbortController | null>(null)
  const mapSection = useRef<HTMLElement | null>(null)
  const rulesDialog = useRef<HTMLDialogElement | null>(null)
  const rulesTrigger = useRef<HTMLButtonElement | null>(null)
  const { data: forecast, loading: forecastLoading, error: forecastError, retry: retryForecast } = useForecast(trip?.id, hour)
  useEffect(() => () => request.current?.abort(), [])
  useEffect(() => {
    const section = mapSection.current
    if (!section || !('IntersectionObserver' in window)) { setMapVisible(true); return }
    // On phones the input form is above the fold; defer the map vendor download
    // until its section approaches the viewport. Once mounted, retain the map.
    const observer = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) {
        setMapVisible(true)
        observer.disconnect()
      }
    }, { rootMargin: '100px' })
    observer.observe(section)
    return () => observer.disconnect()
  }, [])
  useEffect(() => {
    if (!showRules || !rulesDialog.current) return
    const dialog = rulesDialog.current
    // Safari mouse clicks do not focus buttons; restore the known trigger.
    const previousFocus = rulesTrigger.current || document.activeElement
    dialog.showModal()
    return () => {
      dialog.close()
      if (previousFocus instanceof HTMLElement && previousFocus.isConnected) previousFocus.focus({ preventScroll: true })
    }
  }, [showRules])
  const route = trip?.routes.find(route => route.id === selectedRoute)
  const checkpoint = route?.checkpoints.find(cp => cp.id === checkpointId) || null
  const checkpointForecast = forecast?.points.find(point => point.id === checkpointId)

  async function calculate(input: TripInput) {
    request.current?.abort()
    const controller = new AbortController()
    request.current = controller
    setLoading(true); setError(''); setTrip(null); setCheckpointId(null); setHour(0)
    try {
      const result = await api.calculate(input, controller.signal)
      if (controller.signal.aborted) return
      setTrip(result); setSelectedRoute(result.recommended_route_id || result.routes[0]?.id || null)
    } catch (error) { if (!controller.signal.aborted) setError((error as Error).message) }
    finally { if (!controller.signal.aborted) setLoading(false) }
  }

  function chooseRoute(id: string) { setSelectedRoute(id); setCheckpointId(null) }
  function chooseCheckpoint(id: string, revealDetails = false) {
    const owner = trip?.routes.find(route => route.checkpoints.some(point => point.id === id))
    if (owner) {
      setSelectedRoute(owner.id); setCheckpointId(id)
      if (revealDetails) mapSection.current?.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'start' })
    }
  }
  const forecastTime = trip ? new Date(new Date(trip.forecast_base_at).getTime()+hour*3600000).toISOString() : null

  return <div className="app-shell">
    <header className="app-header"><a className="brand" href="/" aria-label="Spotter AI home"><span className="brand-mark"><RouteIcon size={23} /></span><span>spotter<span className="brand-ai">AI</span><small>WEATHER-AWARE ROUTING</small></span></a><div className="header-center"><Truck size={15} /><span>Built for the road ahead</span></div><div className="header-actions"><div className={`service-status ${healthError || (health && !health.routing_configured) ? 'needs-setup' : ''}`}><span className="status-dot" />{healthError ? 'Service offline' : !health ? 'Connecting…' : health.routing_configured ? 'Routing service ready' : 'API setup required'}</div><div className="theme-switch" role="group" aria-label="Color theme"><button type="button" aria-label="Light mode" title="Light mode" aria-pressed={theme === 'light'} onClick={() => setTheme('light')}><Sun size={15} /><span>Light</span></button><button type="button" aria-label="Dark mode" title="Dark mode" aria-pressed={theme === 'dark'} onClick={() => setTheme('dark')}><Moon size={15} /><span>Dark</span></button></div></div></header>
    <div className="workspace"><aside className="sidebar"><TripForm onSubmit={calculate} loading={loading} configured={!!health?.routing_configured} onCancel={() => { request.current?.abort(); setLoading(false) }} /><div className="sidebar-bottom"><div><span className="mini-logo"><CloudSun size={18} /></span><p>Weather changes.<br /><strong>Your plan should keep up.</strong></p></div><button ref={rulesTrigger} className="text-button" onClick={() => setShowRules(true)}><CircleHelp size={14} />How risk is calculated<ArrowRight size={13} /></button></div></aside>
    <main className="main-content">
      <div className="page-title-row"><div><div className="section-eyebrow">THE WEATHER-AWARE ROUTE PLANNER</div><h1>Your route. A clearer outlook.</h1><p>Compare the road ahead, with weather and your load in mind.</p></div><div className="title-icon"><CloudSun size={30} strokeWidth={1.3} /></div></div>
      {(healthError || (health && !health.routing_configured)) && <div className="setup-banner"><Info size={18} /><div><strong>{healthError ? 'Backend connection unavailable' : 'Connect your routing provider to get started'}</strong><p>{healthError || <>Add your TomTom API key to <code>backend/.env</code> and restart Django. Routes and forecasts use real provider data.</>}</p></div><button onClick={retryHealth} disabled={healthRefreshing}>{healthRefreshing ? 'Checking…' : healthError ? 'Retry connection' : 'Check again'}</button></div>}
      {error && <div className="error-banner" role="alert"><TriangleAlert size={18} /><div><strong>We couldn’t calculate this trip</strong><p>{error}</p><small>Update the trip details or use “Find the safest route” to retry.</small></div><button aria-label="Dismiss error" onClick={() => setError('')}>×</button></div>}
      <section ref={mapSection} className="map-section" aria-label="Route map and forecast"><Suspense fallback={<div className="map-loading"><LoaderCircle className="spin" size={24} />Loading map…</div>}>{(mapVisible || trip) ? <MapPanel trip={trip} selectedRoute={selectedRoute} forecast={forecast} heatmap={heatmap} checkpoint={checkpoint} onRoute={chooseRoute} onCheckpoint={chooseCheckpoint} onHeatmap={() => setHeatmap(value => !value)} /> : <div className="map-loading"><LoaderCircle className="spin" size={24} />Loading map?</div>}</Suspense>
      {loading && <div className="calculation-overlay" role="status"><LoaderCircle className="spin" size={22} /><div><strong>Reading the road ahead</strong><span>Finding truck routes and matching weather to arrival times…</span></div></div>}
      {checkpoint && <CheckpointDetails checkpoint={checkpoint} forecast={checkpointForecast} hour={hour} onClose={() => setCheckpointId(null)} />}
      <div className="forecast-panel"><div className="forecast-heading"><span><CloudSun size={18} /><strong>Corridor forecast</strong><span className="forecast-offset">+{hour}h</span></span><span className="forecast-time">{forecastTime ? dateTime(forecastTime) : 'Plan a trip to explore the next 48 hours'}</span></div><input aria-label="Forecast hour offset" type="range" min="0" max="48" step="1" value={hour} disabled={!trip} onChange={event => setHour(Number(event.target.value))} /><div className="slider-labels"><span>Departure</span><span>+12h</span><span>+24h</span><span>+36h</span><span>+48h</span></div><div className="forecast-caption" aria-live="polite">{forecastLoading ? <><LoaderCircle size={12} className="spin" />Loading the selected forecast hour…</> : forecastError ? <><TriangleAlert size={12} />{forecastError}<button onClick={retryForecast}>Retry forecast</button></> : forecast?.missing_count ? <><Info size={12} />{forecast.missing_count} of {forecast.total_points} forecast locations unavailable at this time.</> : <><Info size={12} />Heatmap shows the selected hour. Route risk and recommendations use each checkpoint’s arrival time.</>}</div></div></section>
      <section className="route-comparison"><div className="section-title"><div><span className="section-eyebrow">02</span><h2>Compare your routes</h2>{trip && <span className="count-pill">{trip.routes.length} available</span>}</div><span className="subtle-label">Safety first. Travel time second.</span></div>
      {trip ? <><div className={`recommendation-strip ${trip.recommended_route_id ? '' : 'no-safe'}`}>{trip.recommended_route_id ? <ShieldCheck size={18} /> : <TriangleAlert size={18} />}<p><strong>{trip.recommended_route_id ? `${trip.routes.find(route => route.id === trip.recommended_route_id)?.name} is recommended` : 'No safe route available.'}</strong><span>{trip.recommendation_reason}</span></p></div><div className="route-grid">{trip.routes.map(route => <RouteCard key={route.id} route={route} selected={route.id === selectedRoute} recommended={route.id === trip.recommended_route_id} onSelect={() => chooseRoute(route.id)} />)}</div></> : <div className="routes-empty"><div><RouteIcon size={23} /></div><p><strong>{loading ? 'Your route options are on the way' : 'Good decisions start with a little perspective.'}</strong><span>{loading ? 'Routes will appear here when analysis is complete.' : 'Enter your trip details to compare up to three real truck routes.'}</span></p><span className="empty-step">01 <ArrowRight size={16} /> 02</span></div>}
      </section>
      {route && <section className="checkpoints-section"><div className="section-title"><div><h2>{route.name} checkpoints</h2><span className="count-pill">{route.checkpoints.length}</span></div><span className="subtle-label">Forecast at truck arrival · {trip?.interval_miles} mi sampling</span></div><div className="table-scroll"><table><thead><tr><th>Checkpoint</th><th>Distance</th><th>Arrival time</th><th>Wind</th><th>Rain</th><th>Snow</th><th>Arrival risk</th></tr></thead><tbody>{route.checkpoints.map((point, index) => <tr key={point.id} className={point.id === checkpointId ? 'active-row' : ''} onClick={() => chooseCheckpoint(point.id, true)}><td><button type="button" className="checkpoint-link" aria-controls="checkpoint-details" aria-expanded={point.id === checkpointId}>{index === 0 ? 'Origin' : index === route.checkpoints.length-1 ? 'Destination' : `Checkpoint ${index}`}<ArrowRight size={12} /></button></td><td>{number(point.distance_miles, 1)} mi</td><td>{dateTime(point.eta)}</td><td>{point.weather?.wind_mph == null ? '—' : `${number(point.weather.wind_mph, 1)} mph`}</td><td>{point.weather?.rain_in_per_hour == null ? '—' : `${number(point.weather.rain_in_per_hour, 3)} in/hr`}</td><td>{point.weather?.snow_in_per_hour == null ? '—' : `${number(point.weather.snow_in_per_hour, 3)} in/hr`}</td><td><RiskBadge level={point.risk.level} /></td></tr>)}</tbody></table></div><div className="selected-summary"><span>{number(route.distance_miles)} miles · {duration(route.duration_seconds)}</span><span>{Object.entries(route.summary.risk_miles).map(([level, miles]) => `${level}: ${number(miles, 1)} mi`).join(' · ')}</span></div></section>}
      {trip && <section className="trip-notes"><button onClick={() => setShowNotes(value => !value)} aria-expanded={showNotes}><Info size={14} />Trip notes & provider limitations ({trip.warnings.length}){showNotes ? <ChevronUp size={14} /> : <ChevronDown size={14} />}</button>{showNotes && <ul>{trip.warnings.map(warning => <li key={warning}>{warning}</li>)}</ul>}</section>}
      <footer className="app-footer"><span><Check size={12} />Real routes. Arrival-time forecasts. Transparent risk.</span><span>Routing: TomTom · Weather: <a href="https://open-meteo.com/" target="_blank" rel="noreferrer">Open-Meteo</a></span></footer>
    </main></div>
    {showRules && <div className="modal-backdrop" onClick={() => setShowRules(false)}><dialog ref={rulesDialog} className="rules-modal" aria-label="Weather risk rules" onClick={event => {
      event.stopPropagation()
      const bounds = event.currentTarget.getBoundingClientRect()
      if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) setShowRules(false)
    }} onCancel={() => setShowRules(false)}><div className="section-title"><h2>How risk is calculated</h2><button className="icon-button" onClick={() => setShowRules(false)} aria-label="Close risk rules">×</button></div><p>Each checkpoint uses forecast wind, rain, and snow at the truck’s estimated arrival. The highest severity wins, followed by the supplied cargo-load rules.</p><table><thead><tr><th>Risk</th><th>Wind mph</th><th>Rain in/hr</th><th>Snow in/hr</th></tr></thead><tbody>{[['Low', '<25', '<0.10', '<0.5'], ['Moderate', '25–<35', '0.10–<0.25', '0.5–<1'], ['High', '35–<45', '0.25–<0.50', '1–<2'], ['Severe', '45–<55', '0.50–1.00', '2–3'], ['No Travel', '≥55', '>1.00', '>3']].map(row => <tr key={row[0]}>{row.map((cell, i) => <td key={i}>{cell}</td>)}</tr>)}</tbody></table><p><strong>Load overrides:</strong> wind 45–&lt;55 mph + cargo above 30,000 lb → No Travel. Wind 35–&lt;45 mph + cargo above 40,000 lb → Severe.</p><p>Each road segment takes the more severe endpoint risk. Miles are distance-weighted. Eligible routes rank by Severe miles, High miles, average risk, then travel time. Missing weather is Unknown and blocks a recommendation.</p><p className="field-hint">All displayed times use your device’s timezone. Repeated daylight-saving times resolve to the earlier occurrence. Forecasts are sampled estimates; always verify road restrictions and current conditions.</p></dialog></div>}
  </div>
}
