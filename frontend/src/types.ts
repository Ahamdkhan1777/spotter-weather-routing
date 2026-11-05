import type * as GeoJSON from 'geojson'

export type RiskLevel = 'Low' | 'Moderate' | 'High' | 'Severe' | 'No Travel' | 'Unknown'
export type Coordinates = [number, number]
export interface Place { label: string; coordinates: Coordinates }
export interface Weather { forecast_at: number; wind_mph: number | null; rain_in_per_hour: number | null; snow_in_per_hour: number | null }
export interface Risk { level: RiskLevel; complete: boolean; reason: string; conditions: Record<string, RiskLevel> }
export interface Checkpoint { id: string; coordinates: Coordinates; distance_miles: number; eta: string; weather: Weather | null; risk: Risk }
export interface Route {
  id: string; name: string; geometry: GeoJSON.LineString; distance_miles: number; duration_seconds: number; arrival_at: string; truck_supported: boolean
  checkpoints: Checkpoint[]
  segments: { start_miles: number; end_miles: number; risk: RiskLevel; geometry: GeoJSON.LineString }[]
  summary: { risk_miles: Record<RiskLevel, number>; average_risk: number | null; coverage_percent: number; complete: boolean; blocked: boolean; eligible: boolean }
}
export interface TripInput { origin: string; destination: string; departure_at: string; load_weight_lb: number; interval_miles: number }
export interface Trip {
  id: string; origin: Place; destination: Place; departure_at: string; forecast_base_at: string; load_weight_lb: number; interval_miles: number
  routes: Route[]; recommended_route_id: string | null; recommendation_reason: string; warnings: string[]; providers: Record<string, string>
}
export interface ForecastPoint { id: string; coordinates: Coordinates; kind: 'checkpoint' | 'corridor'; weather: Weather | null; risk: Risk }
export interface Forecast { hour: number; timestamp: string; points: ForecastPoint[]; missing_count: number; total_points: number }
export interface Health { status: string; routing_configured: boolean; demo_mode: boolean }
