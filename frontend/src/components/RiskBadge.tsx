import { AlertTriangle, CircleHelp, ShieldCheck } from 'lucide-react'
import type { CSSProperties } from 'react'
import type { RiskLevel } from '../types'
import { RISK_COLORS } from '../utils'

export function RiskBadge({ level }: { level: RiskLevel }) {
  const Icon = level === 'Unknown' ? CircleHelp : level === 'Low' ? ShieldCheck : AlertTriangle
  return <span className="risk-badge" data-risk={level} style={{ '--risk-color': RISK_COLORS[level] } as CSSProperties}><Icon size={12} />{level}</span>
}
