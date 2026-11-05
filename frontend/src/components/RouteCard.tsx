import { ArrowUpRight, Check, Clock3, ShieldAlert } from 'lucide-react'
import type { Route } from '../types'
import { dateTime, duration, number, RISK_COLORS, RISK_LEVELS } from '../utils'

export function RouteCard({ route, selected, recommended, onSelect }: { route: Route; selected: boolean; recommended: boolean; onSelect: () => void }) {
  const summary = route.summary
  const status = summary.blocked ? 'No Travel' : !summary.complete ? 'Incomplete forecast' : !route.truck_supported ? 'Truck mode unavailable' : recommended ? 'Recommended' : 'Alternative route'
  return <button className={`route-card ${selected ? 'selected' : ''} ${recommended ? 'recommended' : ''}`} onClick={onSelect} aria-pressed={selected}>
    <div className="route-card-top"><span className={`route-status ${summary.eligible ? '' : 'unavailable'}`}>{recommended ? <Check size={12} /> : !summary.eligible ? <ShieldAlert size={12} /> : <span className="tiny-dot" />}{status}</span><ArrowUpRight size={16} /></div>
    <div className="route-title"><h3>{route.name}</h3><span>{number(route.distance_miles)} <small>mi</small></span></div>
    <div className="route-duration"><Clock3 size={13} />{duration(route.duration_seconds)}<span>·</span><span>ETA {dateTime(route.arrival_at)}</span></div>
    <div className="risk-bar" aria-label="Risk miles by severity">{RISK_LEVELS.map(level => <span key={level} title={`${level}: ${number(summary.risk_miles[level], 1)} mi`} style={{ width: `${summary.risk_miles[level]/route.distance_miles*100}%`, background: RISK_COLORS[level] }} />)}</div>
    <div className="route-metrics"><div><span>Severe miles</span><strong className={summary.risk_miles.Severe > 0 ? 'red' : ''}>{number(summary.risk_miles.Severe, 1)}</strong></div><div><span>High miles</span><strong>{number(summary.risk_miles.High, 1)}</strong></div><div><span>Avg. risk / 4</span><strong>{summary.average_risk === null ? 'Unknown' : number(summary.average_risk, 2)}</strong></div></div>
    <div className="route-coverage">{number(summary.coverage_percent)}% weather coverage{summary.blocked && ` · ${number(summary.risk_miles['No Travel'], 1)} No Travel mi`}</div>
  </button>
}
