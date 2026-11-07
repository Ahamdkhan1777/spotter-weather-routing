# Spotter AI — Weather-Aware Truck Routing

A React + Django trip planner that compares actual truck routes using weather at the truck's estimated arrival time. Cargo load affects wind risk; a deterministic, distance-weighted comparison selects an eligible route. An independent 0–48-hour forecast slider explores weather across the trip corridor.

## Features

- Human-readable origin/destination search, local departure date/time, cargo weight in pounds, and 10/25/50-mile checkpoint spacing.
- TomTom truck routing with up to three distinct alternatives; fewer available routes are explained, never fabricated.
- Checkpoints interpolated along road geometry, including the origin, destination, and final partial interval.
- Open-Meteo hourly forecasts at checkpoint ETAs, with explicit unit normalization and missing-data handling.
- Independent wind/rain/snow classification, exact cargo overrides, distance-weighted risk miles, and lexicographic ranking.
- MapLibre alternatives, risk-colored road segments, clickable checkpoints, detailed weather, and route summaries.
- Forecast-backed corridor heatmap with real selected-hour data; slider changes do not alter arrival-time recommendations.
- Responsive layout, loading/cancellation/retry states, provider/setup errors, and accessible text labels alongside colors.
- Saved light/dark theme switch in the header. Both modes keep the clear light basemap. Dark mode is the default; switching preserves the current trip, selected checkpoint, and forecast hour.

There are no user accounts, saved trips, fleet features, or production mock data. Trips are ephemeral calculations cached for one hour.

## Stack and architecture

React 19, TypeScript, Vite, Tailwind CSS 4, MapLibre GL JS, and Lucide; Django 5.2 LTS, Django REST Framework, and Requests.

```text
React inputs → Django validation → TomTom geocoding + truck alternatives
  → cumulative-distance checkpoints + ETAs → batched Open-Meteo forecasts
  → weather + cargo risk → distance-weighted road segments → ranked routes
  → React map, comparisons, and checkpoint table

Forecast slider → cached trip forecast endpoint → selected-hour corridor map
```

```text
backend/
  config/                Environment, URLs, WSGI, production static serving
  routing/               DRF serializers and HTTP endpoints
  services/              Providers, geometry, weather, risk, ranking, orchestration
  tests/                 Calculation, provider, and API integration tests
frontend/
  src/components/        Trip form, map, comparisons, checkpoint details
  src/hooks/             Abortable, debounced, cached forecast retrieval
  src/services/          Typed HTTP client
  e2e/                   Isolated browser fixtures and interaction tests
docs/                    API contract
Dockerfile               Production frontend build + Django runtime
render.yaml              Single-service deployment blueprint
.github/workflows/ci.yml  Backend, frontend, build, and browser checks
```

No database-backed application models are required: normalized `Trip`, `Route`, `Checkpoint`, `Weather`, `Risk`, and `Forecast` response contracts live in `frontend/src/types.ts` and [docs/API.md](docs/API.md). Business logic is separate from HTTP views. Django's unused SQLite default requires no migrations for this app.

## Prerequisites

- Python 3.12–3.14 (verified locally with 3.14; deployment uses 3.13).
- Node.js 22.13+ or 24+ and npm (including ESLint development tooling).
- A TomTom developer API key authorized for Search and Routing.
- Internet access for provider APIs, basemap tiles, glyphs, and browser installation.
- Docker is optional.

## Local setup

Run these from the repository root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
```

Edit `backend/.env` and set `TOMTOM_API_KEY`. Keep `DJANGO_DEBUG=true` locally. Start Django:

```powershell
Set-Location backend
..\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

In another terminal:

```powershell
Set-Location frontend
npm ci
npm run dev
```

Open **http://127.0.0.1:5173**. Vite proxies `/api` to Django at port 8000. Health is at **http://127.0.0.1:8000/api/health/**. The frontend starts without a key and shows setup instructions; route calculation returns an explicit 503 until routing is configured.

After changing `backend/.env`, restart Django. The setup banner rechecks every five seconds while routing is unavailable and also offers **Check again**. Returning to the browser tab refreshes service status, so an old setup message clears without losing trip inputs.

macOS/Linux equivalents use `python3 -m venv .venv`, `.venv/bin/python`, and `cp backend/.env.example backend/.env`. From `backend`, use `../.venv/bin/python manage.py runserver`.

## Environment configuration

| Backend variable | Purpose |
|---|---|
| `TOMTOM_API_KEY` | Required private Search/Routing key; never sent to the browser |
| `DJANGO_DEBUG` | `true` locally; `false` in production |
| `SECRET_KEY` | Unique random production secret; production rejects the supplied development values |
| `ALLOWED_HOSTS` | Comma-separated backend hostnames; Render hostname is included automatically |
| `CORS_ALLOWED_ORIGINS` | Exact frontend origins for split hosting; default local Vite origins |
| `TRUCK_EMPTY_WEIGHT_LB` | Empty vehicle weight, default 18,000 lb; cargo is added before TomTom's kg conversion |
| `TRUCK_HEIGHT_M`, `TRUCK_WIDTH_M`, `TRUCK_LENGTH_M` | Optional real vehicle dimensions in metres; blank/whitespace means unspecified. Configured values must be finite and positive; restart Django after changing them |
| `PROVIDER_TIMEOUT_SECONDS` | Provider read timeout, default 15 seconds; connect timeout is 5 seconds |
| `WEATHER_API_URL` | Open-Meteo forecast endpoint; set customer endpoint for a commercial subscription |
| `OPEN_METEO_API_KEY` | Optional commercial key; server-side only |
| `MAX_WEATHER_LOCATIONS` | Maximum unique weather samples per trip, default 450 |
| `DJANGO_SECURE_SSL_REDIRECT` | Defaults to true in production; disable only for local Docker HTTP checks |

| Frontend variable | Purpose |
|---|---|
| `VITE_API_BASE_URL` | Empty for local proxy or same-origin Docker; full backend origin for split hosting |
| `VITE_MAP_STYLE_URL` | Public MapLibre style URL used in both themes; defaults to CARTO Positron |

Frontend variables are public build-time configuration. Do not place private credentials in any `VITE_*` variable. `.env` files are ignored by Git and Docker.

Get a key from the [TomTom developer portal](https://developer.tomtom.com/). The implementation follows [Calculate Route](https://docs.tomtom.com/routing-api/documentation/tomtom-maps/v1/calculate-route) and [Search](https://docs.tomtom.com/search-api/documentation/search-service/fuzzy-search). TomTom usage quotas depend on the account; a provider may return fewer than the requested two alternatives.

[Open-Meteo documentation](https://open-meteo.com/en/docs) describes the forecast fields and units. Its public API is intended for non-commercial use; check [licensing and pricing](https://open-meteo.com/en/pricing) before commercial deployment. CARTO/OpenStreetMap attribution is displayed by the map. Verify a suitable tile-service plan before substantial production traffic.

## Risk rules and boundaries

Shared boundaries take the higher severity. Wind integer bands extend continuously to the next threshold; e.g. 34.9 mph is Moderate and 44.9 mph is High. Explicit strict upper thresholds are preserved: rain **1.00** and snow **3.00** remain Severe.

| Risk | Wind mph | Rain in/hr | Snow in/hr |
|---|---|---|---|
| Low | `<25` | `<0.10` | `<0.5` |
| Moderate | `25–<35` | `0.10–<0.25` | `0.5–<1` |
| High | `35–<45` | `0.25–<0.50` | `1–<2` |
| Severe | `45–<55` | `0.50–1.00` | `2–3` |
| No Travel | `≥55` | `>1.00` | `>3` |

Each condition is classified independently and the maximum applies. Cargo overrides then apply:

- Wind ≥55 mph: No Travel for any cargo.
- Wind 45–<55 mph and cargo **>30,000 lb**: No Travel.
- Wind 35–<45 mph and cargo **>40,000 lb**: at least Severe.

Exactly 30,000/40,000 lb do not satisfy the respective strict inequalities. Missing, negative, non-finite, or unsupported-unit data is never replaced with zero. Partial weather yields Unknown unless an observed condition already proves No Travel; the coverage flag remains incomplete in either case.

## Checkpoints, ETAs, and weather selection

The backend computes haversine lengths of consecutive road-geometry vertices, calibrates cumulative lengths to the provider's total road distance, and spherically interpolates positions at exact mileage targets. It preserves original road vertices in rendered segments. The origin and destination are always included, with no duplicate terminal checkpoint for an exact interval multiple.

Checkpoint ETA uses TomTom's cumulative distance/travel-time progress, requested with `extendedRouteRepresentation=distance` and `travelTime`. Elapsed time is interpolated between the surrounding provider progress points, so slower road sections receive more time. The profile must cover the entire route with finite, monotone distances/times and totals matching the route summary (within provider rounding). If unavailable or invalid, ETA falls back to `departure + total_duration × cumulative_distance / route_distance` and the trip notes explicitly disclose the uniform-speed estimate. Origin and destination times remain tied to departure and the provider's total duration. Rest stops, hours-of-service rules, and later traffic changes are excluded.

Timestamps are offset-aware UTC internally. The form explicitly uses the device timezone; all displayed times use that timezone, including for trips crossing zones. Nonexistent spring-forward times are rejected; repeated fall-back times resolve to the browser's earlier occurrence. API callers can choose either repeated instant by sending an explicit offset. No naive departure timestamps are accepted.

Hourly forecasts use Unix timestamps in UTC. Rain plus showers represent liquid rainfall; snowfall represents snow depth. Units are read from provider metadata and converted to mph/inches, including metric snowfall cm → inches when necessary. Rain/snow are preceding-hour accumulations: an ETA selects the hour ending at or immediately after that instant. This is an hourly average, not an instantaneous precipitation measurement. Forecasts outside returned timestamps are unavailable; values are not extrapolated.

## Distance weighting and recommendation

Each checkpoint interval takes the **more severe endpoint**. If either endpoint is Unknown, the segment is Unknown unless another endpoint proves No Travel. This conservative choice includes the destination and final partial interval, preserves total miles, and avoids counting checkpoints as distance. Coarser sampling can still miss localized weather; risk miles are estimates and can change with interval selection.

Known risk scores are Low=0, Moderate=1, High=2, Severe=3, No Travel=4. Average risk is `sum(segment miles × score) / total miles` and is **null when weather coverage is incomplete**. Coverage is the distance whose two endpoint forecasts are complete.

Routes are ineligible if any checkpoint proves No Travel, any weather is incomplete, or TomTom reports a non-truck section. Eligible routes rank lexicographically by:

1. Severe miles.
2. High miles.
3. Distance-weighted average risk.
4. Duration seconds.

An exact tie breaks by stable provider route ID. There is no arbitrary weighted optimization score. If no route is eligible, the UI displays **No safe route available** and the reason. A recommendation means best under these supplied assessment rules; dimensions/restrictions still require verification.

## Forecast slider and heatmap

The 0–48-hour slider is anchored to the **trip departure instant**. It requests actual forecasts for that single instant at checkpoint coordinates and at centerline/±12-mile cross-corridor samples approximately every 50 miles along all alternatives. These lateral samples represent a corridor, not additional routing alternatives.

MapLibre renders one heatmap per risk category so color represents risk rather than falsely presenting dense Low-risk samples as High risk. Spatial kernels visualize sparse forecast samples; this is not radar or a continuously observed weather field. Unknown corridor samples have gray markers and an unavailable-count message. Checkpoint details show both arrival-time weather and the slider's selected-hour weather. Road-segment colors and recommendations always retain arrival-time risk.

Forecast requests debounce by 160 ms, cancel stale requests, and cache visited hours in the browser. The map instance is preserved and source data updates in place. Geocoding debounces by 450 ms. Weather requests deduplicate coordinates, batch 25 locations, and use at most three concurrent provider requests; successful weather is cached 15 minutes. Trips expire after one hour or a server restart. Trip forecasts are snapshots; recalculate to refresh them.

## API

See [docs/API.md](docs/API.md) for request/response contracts.

| Method | Endpoint | Behavior |
|---|---|---|
| GET | `/api/health/` | Service and routing configuration state |
| GET | `/api/places/?q=...` | Human-readable location suggestions |
| POST | `/api/routes/calculate/` | Full arrival-time route analysis |
| GET | `/api/trips/{uuid}/` | Cached calculation |
| GET | `/api/trips/{uuid}/forecast/?hour=0..48` | Independent selected-hour forecast |

Validation errors return 400; invalid locations/no route return 422; missing credentials return 503; provider timeout returns 504; rate limiting returns 429; expired trips return 404. Provider details and secrets are not echoed. Forecast provider failures yield Unknown data and explicit warnings rather than a fictitious success.

## Tests and production build

Install backend development tools with `.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt`. ESLint requires Node 20.19+, 22.13+, or 24+. The frontend development dependencies are installed by `npm.cmd ci` in `frontend/`.

```powershell
# From the project root
.\.venv\Scripts\python.exe -m ruff check backend

# From backend/
..\.venv\Scripts\python.exe manage.py check
..\.venv\Scripts\python.exe manage.py test tests --verbosity 2

# From frontend/
npm.cmd run lint
npm test
npm run build
npx playwright install chromium
npm run test:e2e

# Optional quick checks in Chromium, Firefox and WebKit
npx.cmd playwright install firefox webkit
npm.cmd run test:cross-browser
```

Backend tests cover supplied thresholds, load boundaries, invalid weather, geometry and ETA sampling, distance weighting, all ranking priorities, No Travel/incomplete exclusion, provider behavior, and API orchestration. Frontend tests cover inputs and timestamp conversion. Playwright exercises desktop/mobile forms, route results, checkpoint inspection, the forecast slider, errors/retry, and overflow. Browser/API tests use isolated fixtures and do not prove live TomTom authorization. The frontend has no fixture mode.

MapLibre is pinned to 5.24.0 with the upstream attribution-sanitizer security fix backported by `frontend/scripts/patch-maplibre-security.mjs`. Installation, development startup and builds verify/apply this patch; unknown package versions or contents fail closed. Run `npm.cmd run test:security` for patch-integrity regressions. Review this backport before changing the MapLibre pin. Version-based npm audit still reports 13 affected packages: this backported production dependency and 12 development-only entries. Retained tooling findings concern tinypool prototype-pollution gadgets, unused standalone Vitest mock-server plugins, and minimatch's unconfigured higher-optimization path. Use trusted local tests/configuration and keep development servers private; these findings are not a claim of zero security risk. Published fixes require incompatible dependency changes, including MapLibre 6.4.1+, so no forced upgrades or audit suppressions were applied.

GitHub Actions runs backend/frontend tests, the production build and Chromium browser checks. Local audit reports, manual test records, optional helper scripts and walkthrough material are archived in the ignored `EXTRANEOUS/` folder.

## Deployment

The supplied Docker image builds React and serves it with Django/WhiteNoise. All APIs and assets share one origin. Gunicorn uses **one process with four threads** because trip/weather caching is deliberately process-local. Do not add workers/replicas without replacing the cache with a shared backend.

1. Publish this project as a separate GitHub repository.
2. In Render, create a Blueprint from that repository using `render.yaml`, or create a Docker web service.
3. Supply `TOMTOM_API_KEY`. The blueprint generates `SECRET_KEY` and disables debug.
4. Adjust empty weight and dimensions for the vehicle. Review the selected service plan and provider licenses.
5. Deploy, open the returned HTTPS URL, check `/api/health/`, calculate a real trip, inspect checkpoint weather, and move the slider.

No database provisioning or migration is needed. See [Render's Django guide](https://render.com/docs/deploy-django) for hosting background. This project uses Docker and an ephemeral cache rather than the guide's database-backed example. No free-tier or deployment-success claim is made.

Local Docker verification:

```powershell
docker build -t spotter-routing .
# Set a unique SECRET_KEY in backend/.env before using production mode.
docker run --rm -p 8000:8000 --env-file backend/.env -e DJANGO_DEBUG=false -e DJANGO_SECURE_SSL_REDIRECT=false spotter-routing
```

Open http://localhost:8000 for this local Docker check. Public production deployments retain the default HTTPS redirect; do not disable it on Render.

| Deliverable | Current link/status |
|---|---|
| GitHub repository | Local Git repository created; publishing requires a connected GitHub account |
| Hosted frontend/backend | Docker/Render files prepared; no hosted URL verified |
| Loom | Recording and upload not performed |

## Known limitations

- Live TomTom geocoding and the three-route Dallas → Austin truck flow were verified locally. A valid server-side API key remains required in each environment; automated fixtures alone do not verify account authorization.
- Forecast horizon varies by weather model, field, location, and departure; requested 16-day data is not a guarantee of complete coverage.
- Only cargo weight is entered by the user. Truck empty weight/dimensions are operator configuration; unspecified dimensions are not checked.
- The route recommendation follows the assessment's load rules exactly, including their supplied heavier-load wind overrides.
- Checkpoint ETAs interpolate provider timing points, with a disclosed uniform-speed fallback when unavailable. Conservative endpoint segment risks remain sampled estimates.
- Corridor forecasts are sparse spatial samples rendered as kernels, not radar.
- The in-memory cache is ephemeral and single-process; a restart invalidates trips and the UI requests recalculation.
- Provider, map tile, and forecast licensing/quotas must be suitable for actual traffic. Extensive trips exceeding 450 unique samples return a clear sampling-limit error; choose a coarser interval or shorter trip.
- The publicly accessible evaluation API has per-process anonymous calculation/search throttling; sustained production use should add shared throttling at the platform edge.
