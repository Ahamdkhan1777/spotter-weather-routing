# HTTP contracts

The base path is `/api`. Responses use JSON. Internal and returned departure/ETA timestamps are ISO 8601 with a UTC offset. Coordinates are consistently GeoJSON `[longitude, latitude]`. Weather `forecast_at` is Unix **seconds**, not milliseconds.

## POST /routes/calculate/

```json
{
  "origin": "Dallas, TX",
  "destination": "Austin, TX",
  "departure_at": "<future ISO 8601 timestamp, including Z or an explicit offset>",
  "load_weight_lb": 35000,
  "interval_miles": 25
}
```

Location strings: 2–200 characters, trimmed. Load: finite number, >0 and ≤200,000 lb. Interval: 10/25/50, default 25. Departure: timezone-aware, no more than five minutes in the past or 15 days ahead. Identical origin/destination strings and identical resolved coordinates are rejected.

The successful response contains:

| Field | Type/content |
|---|---|
| `id` | Trip UUID, valid in ephemeral server cache for up to 3600 seconds |
| `origin`, `destination` | `{label, coordinates: [lon,lat]}` |
| `departure_at`, `forecast_base_at` | Departure timestamp; the latter anchors the slider |
| `load_weight_lb`, `interval_miles` | Normalized inputs |
| `routes` | One to three distinct route objects |
| `recommended_route_id` | Eligible route ID or `null` |
| `recommendation_reason` | Human-readable ranking or exclusion explanation |
| `warnings` | Provider limitations, missing-data and sampling disclosures |
| `providers` | Routing/weather provider names |
| `expires_in_seconds` | Cache lifetime, not durable persistence |

### Route

`id`, `name`, original GeoJSON `geometry`, `distance_miles`, `duration_seconds`, offset-aware `arrival_at`, `truck_supported`, `checkpoints`, `segments`, and `summary`.

### Checkpoint

`id`, `[lon,lat]` `coordinates`, `distance_miles`, `eta`, `weather` (nullable), and `risk`.

Weather fields: `forecast_at`, `wind_mph`, `rain_in_per_hour`, `snow_in_per_hour`. Individual values can be null; they are not converted to zero. Hourly rainfall includes rain and showers, excluding snowfall water equivalent.

Risk fields: `level` (`Low`, `Moderate`, `High`, `Severe`, `No Travel`, `Unknown`), `complete`, individual `conditions`, and `reason`.

### Segment and summary

A segment has `start_miles`, `end_miles`, `risk`, and a GeoJSON LineString `geometry` preserving road vertices. Risk is the more severe endpoint, conservatively Unknown if either endpoint lacks weather, unless No Travel is already known.

Summary has `risk_miles` keyed by every risk level including Unknown, `average_risk` (0–4 or null), `coverage_percent`, `complete`, `blocked`, and `eligible`. Risk miles sum to route distance; percentages and averages are distance-weighted. Unknown weather is excluded from safe recommendations, not from total distance.

## GET /trips/{id}/forecast/?hour=0..48

Returns `hour`, ISO `timestamp`, `points`, `missing_count`, and `total_points`. Each point has `id`, `coordinates`, `kind` (`checkpoint` or `corridor`), `weather`, and `risk`. The timestamp is trip departure plus the selected integer hours. Checkpoint point IDs match arrival-time checkpoint IDs, allowing side-by-side inspection.

This endpoint reads previously retrieved forecast series; it does not change route risk, rankings, or the cached calculation. No new provider request is needed for a slider change. Expired trips return 404 and require recalculation.

## Other endpoints

- `GET /health/`: `{status: "ok", routing_configured: boolean, weather_provider: "Open-Meteo", demo_mode: false}`.
- `GET /places/?q=...`: `{places: [{label, coordinates}]}`; query length 2–200.
- `GET /trips/{id}/`: complete cached route result.

## Errors

Provider errors use `{error: {code, message}}` with 422 (invalid location/no routes/sampling limit), 429 (provider limit), 502 (provider/network/invalid response), 503 (credentials), or 504 (timeout). DRF validation errors use field-keyed message arrays with 400. Expired trips use `trip_expired`/404. Forecast provider failures during calculation return explicit warnings, incomplete coverage, and Unknown data; no route is recommended on that basis.

No raw third-party exception URLs or API keys are included. Anonymous search/calculation requests are limited to 120/hour/process. The forecast endpoint is unthrottled to support slider interaction and only reads cached data.
