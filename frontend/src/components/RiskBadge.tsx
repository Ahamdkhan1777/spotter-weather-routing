import { AlertTriangle, CircleHelp, ShieldCheck } from 'lucide-react'
import type { RiskLevel } from '../types'
import { RISK_COLORS } from '../utils'

export function RiskBadge({ level }: { level: RiskLevel }) {
  const Icon = level === 'Unknown' ? CircleHelp : level === 'Low' ? ShieldCheck : AlertTriangle
  return <span className="risk-badge" style={{ color: RISK_COLORS[level], backgroundColor: `${RISK_COLORS[level]}14` }}><Icon size={12} />{level}</span>
}
