import { useEffect, useRef, useState } from 'react'
import maplibregl from 'maplibre-gl'
import type { GeoJSONSource, Map as MapType } from 'maplibre-gl'
import type * as GeoJSON from 'geojson'
import { Expand, Layers, Map, MapPin, TriangleAlert } from 'lucide-react'
import type { Checkpoint, Forecast, RiskLevel, Trip } from '../types'
import { RISK_COLORS, RISK_LEVELS } from '../utils'
import 'maplibre-gl/dist/maplibre-gl.css'

interface Props {
  trip: Trip | null; selectedRoute: string | null; forecast: Forecast | null; heatmap: boolean; checkpoint: Checkpoint | null
  onRoute: (id: string) => void; onCheckpoint: (id: string) => void; onHeatmap: () => void
}
const empty: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features: [] }
const sourceIds = ['routes', 'segments', 'checkpoints', 'forecast']
const mapStyle = import.meta.env.VITE_MAP_STYLE_URL || 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json'
const riskExpression: maplibregl.ExpressionSpecification = ['match', ['get', 'risk'],
  'Low', RISK_COLORS.Low, 'Moderate', RISK_COLORS.Moderate, 'High', RISK_COLORS.High,
  'Severe', RISK_COLORS.Severe, 'No Travel', RISK_COLORS['No Travel'], RISK_COLORS.Unknown]

function fitTrip(map: MapType, trip: Trip) {
  const bounds = new maplibregl.LngLatBounds()
  trip.routes.forEach(route => route.geometry.coordinates.forEach(point => bounds.extend(point as [number, number])))
  map.fitBounds(bounds, { padding: { top: 80, bottom: 90, left: 70, right: 70 }, duration: 700, maxZoom: 12 })
}

export default function MapPanel(props: Props) {
  const container = useRef<HTMLDivElement>(null)
  const mapRef = useRef<MapType | null>(null)
  const latest = useRef(props)
  latest.current = props
  const fitted = useRef('')
  const [ready, setReady] = useState(false)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    if (!container.current) return
    let map: MapType
    let interactionsBound = false
    let loadTimeout: ReturnType<typeof setTimeout> | undefined
    setReady(false)
    setError('')
    try {
      map = new maplibregl.Map({ container: container.current, style: mapStyle, center: [-98.3, 37.3], zoom: 3.8, attributionControl: { compact: true } })
      mapRef.current = map
      loadTimeout = setTimeout(() => {
        if (!map.isStyleLoaded()) setError('The basemap is taking too long to load. Check your connection and retry; route summaries remain available.')
      }, 20000)
      map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'bottom-right')
      map.on('style.load', () => {
        clearTimeout(loadTimeout)
        for (const id of sourceIds) map.addSource(id, { type: 'geojson', data: empty })
        RISK_LEVELS.filter(level => level !== 'Unknown').forEach((level, index) => {
          const color = RISK_COLORS[level]
          const rgb = color.match(/\w\w/g)!.map(value => parseInt(value, 16)).join(',')
          map.addLayer({ id: `heat-${index}`, type: 'heatmap', source: 'forecast', filter: ['==', ['get', 'risk'], level], paint: {
            'heatmap-radius': ['interpolate', ['linear'], ['zoom'], 3, 22, 10, 48],
            'heatmap-weight': 1, 'heatmap-intensity': 0.8, 'heatmap-opacity': 0.55,
            'heatmap-color': ['interpolate', ['linear'], ['heatmap-density'], 0, `rgba(${rgb},0)`, 0.35, `rgba(${rgb},0.38)`, 1, color],
          } })
        })
        map.addLayer({ id: 'unknown-forecast', type: 'circle', source: 'forecast', filter: ['==', ['get', 'risk'], 'Unknown'], paint: { 'circle-radius': 5, 'circle-color': '#84939b', 'circle-opacity': 0.2, 'circle-stroke-color': '#84939b', 'circle-stroke-width': 1 } })
        map.addLayer({ id: 'route-casing', type: 'line', source: 'routes', layout: { 'line-join': 'round', 'line-cap': 'round' }, paint: { 'line-color': '#ffffff', 'line-width': 9 } })
        map.addLayer({ id: 'route-lines', type: 'line', source: 'routes', layout: { 'line-join': 'round', 'line-cap': 'round' }, paint: { 'line-color': '#6c8298', 'line-width': 4, 'line-opacity': 0.8 } })
        map.addLayer({ id: 'risk-segments', type: 'line', source: 'segments', layout: { 'line-join': 'round', 'line-cap': 'round' }, paint: { 'line-color': riskExpression, 'line-width': 5 } })
        map.addLayer({ id: 'checkpoint-circles', type: 'circle', source: 'checkpoints', paint: { 'circle-radius': ['case', ['get', 'endpoint'], 7, 4.5], 'circle-color': riskExpression, 'circle-stroke-color': '#ffffff', 'circle-stroke-width': 2 } })
        map.addLayer({ id: 'endpoint-labels', type: 'symbol', source: 'checkpoints', filter: ['==', ['get', 'endpoint'], true], layout: { 'text-field': ['get', 'label'], 'text-size': 12, 'text-offset': [0, -1.5], 'text-anchor': 'bottom' }, paint: { 'text-color': '#203c35', 'text-halo-color': '#ffffff', 'text-halo-width': 2 } })
        // Style changes rebuild layers; keep the interaction listeners registered once.
        if (!interactionsBound) {
          map.on('click', 'checkpoint-circles', event => { const id = event.features?.[0]?.properties?.id; if (id) latest.current.onCheckpoint(String(id)) })
          map.on('click', 'route-lines', event => { if (map.queryRenderedFeatures(event.point, { layers: ['checkpoint-circles'] }).length) return; const id = event.features?.[0]?.properties?.id; if (id) latest.current.onRoute(String(id)) })
          for (const layer of ['checkpoint-circles', 'route-lines']) {
            map.on('mouseenter', layer, () => { map.getCanvas().style.cursor = 'pointer' })
            map.on('mouseleave', layer, () => { map.getCanvas().style.cursor = '' })
          }
          interactionsBound = true
        }
        setReady(true)
        setError('')
      })
      map.on('error', event => { if (!map.isStyleLoaded()) setError(event.error?.message?.includes('WebGL') ? 'Your browser could not initialize WebGL.' : 'Map tiles could not load. Check your connection or retry.') })
    } catch { setError('Map rendering is unavailable. Enable WebGL or try another browser. Route summaries and checkpoints are still available.'); return }
    const resize = new ResizeObserver(() => map.resize())
    resize.observe(container.current)
    return () => { clearTimeout(loadTimeout); resize.disconnect(); map.remove(); mapRef.current = null; fitted.current = '' }
  }, [attempt])

  useEffect(() => {
    const map = mapRef.current
    if (!ready || !map) return
    const trip = props.trip
    const routes: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features: trip?.routes.map(route => ({ type: 'Feature', geometry: route.geometry, properties: { id: route.id } })) || [] }
    const segments: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features: trip?.routes.flatMap(route => route.segments.map(segment => ({ type: 'Feature' as const, geometry: segment.geometry, properties: { route_id: route.id, risk: segment.risk } }))) || [] }
    const checkpoints: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features: trip?.routes.flatMap(route => route.checkpoints.map((checkpoint, index) => ({ type: 'Feature' as const, geometry: { type: 'Point' as const, coordinates: checkpoint.coordinates }, properties: { id: checkpoint.id, route_id: route.id, risk: checkpoint.risk.level, endpoint: index === 0 || index === route.checkpoints.length-1, label: index === 0 ? 'ORIGIN' : index === route.checkpoints.length-1 ? 'DESTINATION' : '' } }))) || [] }
    for (const [id, data] of [['routes', routes], ['segments', segments], ['checkpoints', checkpoints]] as const) (map.getSource(id) as GeoJSONSource).setData(data)
    map.setPaintProperty('risk-segments', 'line-opacity', ['case', ['==', ['get', 'route_id'], props.selectedRoute || ''], 1, 0.4])
    map.setPaintProperty('risk-segments', 'line-width', ['case', ['==', ['get', 'route_id'], props.selectedRoute || ''], 5.5, 3])
    map.setPaintProperty('checkpoint-circles', 'circle-opacity', ['case', ['==', ['get', 'route_id'], props.selectedRoute || ''], 1, 0.45])
    if (trip && fitted.current !== trip.id) { fitTrip(map, trip); fitted.current = trip.id }
  }, [ready, props.trip, props.selectedRoute])

  useEffect(() => {
    const map = mapRef.current
    if (!ready || !map) return
    const points: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features: props.forecast?.points.filter(point => point.kind === 'corridor').map(point => ({ type: 'Feature', geometry: { type: 'Point', coordinates: point.coordinates }, properties: { risk: point.risk.level } })) || [] }
    ;(map.getSource('forecast') as GeoJSONSource).setData(points)
    for (const id of [...RISK_LEVELS.filter(level => level !== 'Unknown').map((_, i) => `heat-${i}`), 'unknown-forecast']) map.setLayoutProperty(id, 'visibility', props.heatmap ? 'visible' : 'none')
  }, [ready, props.forecast, props.heatmap])

  useEffect(() => {
    if (ready && props.checkpoint) mapRef.current?.easeTo({ center: props.checkpoint.coordinates, duration: 500 })
  }, [ready, props.checkpoint])

  return <div className="map-wrapper" data-map-theme="light" data-map-status={ready ? 'ready' : error ? 'error' : 'loading'}>
    <div ref={container} className="map-canvas" aria-label="Interactive truck route and weather map" />
    <div className="map-top-left"><div className="map-label"><Map size={14} />{props.trip ? 'Trip corridor' : 'Your road ahead'}</div>{props.trip && <span className="map-note">Route colors: weather at truck arrival</span>}</div>
    <div className="map-actions"><button className={props.heatmap ? 'active' : ''} onClick={props.onHeatmap} aria-pressed={props.heatmap}><Layers size={15} />Weather layer</button><button onClick={() => { if (props.trip && mapRef.current && ready) fitTrip(mapRef.current, props.trip) }} disabled={!props.trip || !ready} aria-label="Fit all routes on map" title="Fit all routes"><Expand size={16} /></button></div>
    {!props.trip && !error && <div className="map-empty"><div><MapPin size={24} /></div><h3>Every mile, a little more informed.</h3><p>Plan your trip to compare routes and see<br />the weather along the way.</p></div>}
    {error && <div className="map-error" role="alert"><TriangleAlert size={22} /><p>{error}</p><button onClick={() => setAttempt(value => value+1)}>Retry map</button></div>}
    <div className="map-legend"><span>WEATHER RISK</span>{RISK_LEVELS.map((level: RiskLevel) => <span key={level}><i style={{ background: RISK_COLORS[level] }} />{level}</span>)}</div>
  </div>
}
