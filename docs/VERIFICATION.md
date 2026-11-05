# Verification record

This records checks actually executed during implementation. Provider fixtures are used only in tests; they are not part of the production routing flow.

| Check | Result |
|---|---|
| Separate Git root | Verified project root, independent of the parent user-directory repository |
| `python manage.py check` | Passed, no Django system-check issues |
| `python manage.py test tests --verbosity 1` | **38 passed**, zero failures |
| `npm test` | **6 passed**, zero failures |
| `npm run build` | Passed TypeScript compilation and Vite production build |
| `npm run test:e2e` | **6 passed** in Chromium, zero failures |
| Live Open-Meteo request | Passed: 72 real hourly forecasts and response-metadata unit normalization |
| Docker multi-stage build | Passed: Node frontend build, Python runtime, Gunicorn installed |
| Backend tests inside final Linux/Python 3.13 image | **38 passed**, zero failures |
| Container root page | HTTP 200, production React index verified |
| Container `/api/health/` | HTTP 200, real Django response, demo mode false |
| Container JS and CSS assets | HTTP 200, production asset content verified |
| Live TomTom geocoding and routing | **Not verified: API key not configured** |
| Public hosting | **Not deployed: account connection required** |
| GitHub publishing | **Not published: account connection required** |
| Loom recording/upload | **Not performed; script prepared** |

## Calculation and API coverage

- Exact supplied wind/rain/snow thresholds and fractional wind intervals.
- Strict cargo thresholds at 30,000 and 40,000 lb.
- Independent conditions, maximum severity, and cargo overrides.
- Missing, invalid, non-finite, and unsupported-unit weather.
- Preserving observed No Travel even when other weather is missing.
- Mileage-based checkpoint spacing for all three intervals, final partial intervals, and destination deduplication.
- Road-vertex preservation, cumulative ETA, midnight crossing, antimeridian interpolation, and invalid geometry/duration rejection.
- Distance-weighted summaries, conservative endpoint segment risk, incomplete coverage, and uniform-risk consistency across sampling intervals.
- All four lexicographic ranking priorities, deterministic ties, No Travel exclusion, incomplete forecasts, and unsupported truck sections.
- Batched/cached weather, ETA-hour selection, out-of-horizon forecasts, showers, and metric-to-imperial conversions.
- Missing credentials, duplicate alternatives, no routes, timeouts, rate limits, validation, and expired trips.
- Explicit UTC offsets preserve both occurrences of a repeated daylight-saving hour.
- Orchestrated route calculation and slider endpoints remain independent with no extra weather request on slider movement.

## Browser coverage

1. Desktop trip calculation, loaded MapLibre style and usable canvas dimensions, checkpoint inspection, +48-hour forecast, and unchanged arrival-time recommendation.
2. Mobile missing-credentials/setup state, disabled forecast before a trip, and no horizontal page overflow.
3. Provider error followed by a successful retry.
4. Mobile calculated trip, destination inspection, and no page overflow.
5. Three route cards and selection of another alternative.
6. All-unsafe trip displays No safe route available and no recommended card.

Desktop/mobile screenshots were captured and inspected. Screenshot review exposed a CSS ordering conflict that collapsed the MapLibre canvas; the corrected selector gives it explicit dimensions, and a regression assertion now checks that the loaded map is larger than 500×350 on desktop. Screenshots and Playwright traces stay in ignored `frontend/test-results/`.

## Production notes

The build emits a size notice for the MapLibre library (approximately 285 KB gzipped). It is split from the main application and loaded with the lazy map component. This is a notice, not a failed build.

The production image serves frontend/API under one origin. It uses a single Gunicorn process with four threads because the forecast/trip cache is process-local. A restart or new replica invalidates cached trips; the API returns an explicit expired-trip error.

HTTP container checks can be repeated with `python scripts/verify_http.py http://127.0.0.1:8001` against a running local production container with the HTTPS redirect disabled for that local check. Public hosting retains HTTPS enforcement.

## Assessment readiness

| Original requirement | State |
|---|---|
| React + Django, input form, validation | Complete |
| Up to three actual routing alternatives | Implementation complete; live verification blocked by TomTom key |
| Geometry-based 10/25/50-mile checkpoints and ETA | Complete; automated calculation coverage |
| Arrival-time weather | Complete; integration fixtures plus live weather-provider verification |
| Exact weather/load rules and deterministic ranking | Complete; tested |
| Map, alternatives, checkpoints, ETAs, summaries | Complete; browser-tested with isolated route fixtures |
| Forecast-backed corridor layer and 0–48-hour slider | Complete; provider-backed implementation and browser/API tests |
| GitHub repository URL | Blocked by external account connection; local repository prepared |
| Hosted application URL | Blocked by external account/key configuration; deployment files prepared |
| 5–10-minute Loom | Partially complete: walkthrough script prepared; actual recording outstanding |

This is a tested local implementation, not a claim that external submission deliverables have been completed.
