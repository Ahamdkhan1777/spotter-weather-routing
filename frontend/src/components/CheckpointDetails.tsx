import { CloudRain, Snowflake, Wind, X, MapPin } from 'lucide-react'
import type { Checkpoint, ForecastPoint } from '../types'
import { dateTime, number } from '../utils'
import { RiskBadge } from './RiskBadge'

function WeatherValues({ point }: { point: { weather: Checkpoint['weather'] } }) {
  return <div className="weather-values">{[
    { Icon: Wind, label: 'Wind', value: point.weather?.wind_mph, unit: 'mph', digits: 1 },
    { Icon: CloudRain, label: 'Rain', value: point.weather?.rain_in_per_hour, unit: 'in/hr', digits: 3 },
    { Icon: Snowflake, label: 'Snow', value: point.weather?.snow_in_per_hour, unit: 'in/hr', digits: 3 },
  ].map(({ Icon, label, value, unit, digits }) => <div key={label}><Icon size={16} /><span>{label}</span><strong>{value == null ? '—' : number(value, digits)} <small>{unit}</small></strong></div>)}</div>
}

export function CheckpointDetails({ checkpoint, forecast, hour, onClose }: { checkpoint: Checkpoint; forecast?: ForecastPoint; hour: number; onClose: () => void }) {
  return <aside id="checkpoint-details" className="checkpoint-detail" aria-label="Checkpoint details">
    <div className="checkpoint-detail-top"><div><span className="section-eyebrow">CHECKPOINT</span><h3><MapPin size={16} />Mile {number(checkpoint.distance_miles, 1)}</h3></div><button className="icon-button" onClick={onClose} aria-label="Close checkpoint details"><X size={17} /></button></div>
    <p className="coordinate-label">{checkpoint.coordinates[1].toFixed(4)}, {checkpoint.coordinates[0].toFixed(4)}</p>
    <div className="checkpoint-section"><div className="detail-subheading"><strong>At truck arrival</strong><RiskBadge level={checkpoint.risk.level} /></div><p>{dateTime(checkpoint.eta)}</p><WeatherValues point={checkpoint} /><p className="risk-reason">{checkpoint.risk.reason}</p>{checkpoint.weather && <small className="field-hint">Forecast hour ending {dateTime(checkpoint.weather.forecast_at)}</small>}</div>
    <div className="checkpoint-section"><div className="detail-subheading"><strong>Corridor forecast · +{hour}h</strong>{forecast && <RiskBadge level={forecast.risk.level} />}</div>{forecast ? <><WeatherValues point={forecast} /><p className="risk-reason">{forecast.risk.reason}</p>{forecast.weather && <small className="field-hint">Forecast hour ending {dateTime(forecast.weather.forecast_at)}</small>}</> : <p className="field-hint">Forecast not loaded for this hour.</p>}</div>
  </aside>
}
