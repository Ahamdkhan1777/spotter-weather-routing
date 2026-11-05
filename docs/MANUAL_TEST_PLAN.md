# Weather routing manual acceptance tests

This checklist contains **314 distinct cases**, including **233 isolated checks** for exact boundaries and provider failures. Every original assessment requirement maps to a case group. This is requirements coverage, not a claim of measured 100% code coverage or a guarantee that no unlisted defect exists.

## How to work through the cases

1. Start Django on port 8000 and React on port 5173. Keep both terminals running.
2. Start with SMK-01 through SMK-08, then input cases, map/slider cases, and the controlled calculations.
3. Open `docs/MANUAL_TEST_RESULTS.csv` in Excel or another spreadsheet. Change Status to `Pass`, `Fail`, `Blocked`, or `Not applicable`; record actual results and screenshot/error evidence. All cases start as `Not run` for your own testing.
4. Run controlled cases one at a time from the project root with the active virtual environment: `python scripts/manual_checks.py --case WND-03`. You can also use `.\.venv\Scripts\python.exe` instead of `python`.
5. Controlled checks run against application functions or isolated Django handlers with synthetic provider responses. They block live HTTP, do not alter your `.env`, do not restart services, and do not populate the web server's cache. They prove calculation/error paths; they do not replace browser testing of real providers.
6. Share failed case IDs with inputs, expected and actual results, and a screenshot or error. Do not include API keys or `.env` contents.

`python scripts/manual_checks.py --list` lists IDs. `python scripts/manual_checks.py --all-controlled` runs all isolated checks but does not mark your manual results as passed. `python scripts/manual_checks.py --export` regenerates the checklist and preserves existing CSV Status/Actual result/Notes values by ID. Cases without isolated commands must be performed in the browser or host dashboard.

## Baseline inputs and interpretation

- Normal trip: **Dallas, TX → Austin, TX**, **departure one hour from the current time**, **35,000 lb cargo**, **25-mile interval**. Generate a fresh departure instead of copying an old date.
- Unless a row says otherwise, keep this baseline and change only the stated field. Reuse one calculation for map/card/slider inspections to reduce provider calls.
- Boundary weather checks default to cargo **10,000 lb**, with other weather conditions **0**, so cargo overrides cannot accidentally alter the basic wind table.
- Weather values use **wind mph, rain in/hr, snowfall in/hr**. Cargo thresholds are strict `>`; wind bands extend continuously to the next threshold. Rain exactly **1.00** and snow exactly **3.00** stay Severe.
- A recommendation is allowed only when arrival-time weather is complete, there are no No Travel conditions, and truck mode is supported. Different departure times can legitimately change the winner.
- Live routes, mileage, travel times, and weather change. Verify the response and invariants; do not require last run's exact miles, exactly three alternatives, or a particular weather color.
- If every route is unsafe or incomplete, an explicit no-safe-route result is correct. A service, licensing, or quota failure should be recorded with the actual error; do not automatically call it a calculation defect.
- The form rejects past departures; the API deliberately allows up to five minutes of clock skew. Frozen-clock DATE checks use November 6, 2026 at 12:00 UTC without changing the device/server clock. GEO calculations use a synthetic departure at 23:00 UTC to test midnight crossing.
- While inspecting the slider, route lines and recommendations retain **truck-arrival** risk; the corridor layer and second checkpoint-weather section use **departure + selected hours**. Identical real weather across hours is possible; inspect requested timestamps/data rather than requiring a visual color change.
- Preserve secrets and the real key. Use isolated ERR/API cases for missing-key/rate-limit/timeout scenarios. Do not repeatedly flood the live service to trigger throttling; search/calculation requests are limited to 120/hour/process.
- Production checks are **Blocked until deployment**, not Pass. Browser failures remain failures even when an isolated calculation passes.

## Recording results

P0 means essential routing/safety behavior, P1 means normal correctness/usability, and P2 means final operational/submission checks. Priorities and full step descriptions are in the CSV. Do not use `Not applicable` for a required feature merely because it failed; use `Fail` or `Blocked` and explain the cause.

## Findings from preparation

The preparation run executed all 233 isolated checks: **231 passed and 2 failed**. INP-18 accepts JSON boolean `true` as cargo weight instead of rejecting it. DATE-09 raises `ValueError` for an impossible calendar date instead of returning a normal validation error. Keep these as genuine failures to verify, not setup problems. Application behavior is left unchanged while you run the acceptance cases. The CSV still starts as `Not run` for your own results. The 320-pixel layout and keyboard dialog behavior also deserve manual inspection; no pass is claimed for those unexecuted browser cases.

## Requirement coverage

| Requirement | Case groups |
|---|---|
| Inputs and human-readable locations | SMK, LOC, VAL, INP |
| Departure, UTC, midnight and DST | TIME, DATE, GEO |
| Up to three distinct real truck routes | SMK, RTE, FLOW |
| Actual road geometry, 10/25/50 miles, final partial interval | SMK, GEO, SUM |
| Arrival-time weather, units and available horizon | WTH, TIME, FLOW |
| Every wind, rain, snow boundary and cargo override | WND, RAN, SNW, LDR, MIX, MIS |
| Distance-weighted miles, Unknown and No Travel exclusion | SUM, RNK, FLOW |
| Exact recommendation priority order and ties | RNK |
| Map, checkpoints, ETAs, summaries, responsive behavior | MAP |
| Real corridor heatmap and 0–48-hour exploration | SLD, FLOW, API |
| Provider errors, timeout, rate limit, cache and recovery | ERR, WTH, API, REC |
| Performance, private configuration and submission | OPS |

## Startup and normal trips

| ID | Method | Sample inputs and action | Expected result |
|---|---|---|---|
| SMK-01 | Browser | Backend http://127.0.0.1:8000/api/health/ — Open the URL. | HTTP 200; status ok; routing_configured true; demo_mode false. |
| SMK-02 | Browser | Frontend http://127.0.0.1:5173 — Open the app with both terminals running. | Routing service ready; no setup banner; usable form and basemap. |
| SMK-03 | Browser | Dallas, TX → Austin, TX; departure +1h; 35,000 lb; 25 mi — Calculate; inspect resolved city labels and results. | 1–3 real distinct routes, honest warnings if fewer, weather coverage and recommendation or an explicit safety exclusion. |
| SMK-04 | Browser | Dallas, TX → Austin, TX; 10,000 lb; 10 mi — Calculate once; inspect first and last checkpoints. | 10-mi spacing, origin and destination included, final partial segment handled. |
| SMK-05 | Browser | Dallas, TX → Austin, TX; 10,000 lb; 50 mi — Calculate; compare checkpoint density with SMK-04. | Fewer checkpoints, 50-mi spacing; never count checkpoints as hazardous miles. |
| SMK-06 | Browser | Dallas, TX → Irving, TX; 10,000 lb; 50 mi — Calculate a short trip. | For a returned trip shorter than 50 mi: only origin and destination; otherwise follow actual distance. |
| SMK-07 | Browser | New York, NY → Boston, MA; 30,000 lb; 25 mi — Calculate; inspect timezone-labelled ETAs. | Real provider geometry and weather, or a clear provider restriction/error; no fixed route count assumption. |
| SMK-08 | Browser | Toronto, ON, Canada → Ottawa, ON, Canada; 10,000 lb; 50 mi — Calculate; inspect distance/weather units. | Miles, mph, inches and pounds remain consistent outside the US; disclose provider limitations. |

## Location entry

| ID | Method | Sample inputs and action | Expected result |
|---|---|---|---|
| LOC-01 | Browser | Origin empty — Clear Origin and submit. | Required-field validation; no calculation request. |
| LOC-02 | Browser | Destination empty — Clear Destination and submit. | Required-field validation; no calculation request. |
| LOC-03 | Browser | Origin spaces only — Enter spaces in Origin and submit. | Useful validation; never treat blank text as a location. |
| LOC-04 | Browser | Both fields Dallas, TX — Use the same origin and destination. | Rejected; user can correct and retry. |
| LOC-05 | Browser | Origin Dallas, TX; destination dallas, tx — Submit case-only duplicate locations. | Rejected as the same location. |
| LOC-06 | Browser | Origin and destination both " Dallas, TX " — Include surrounding spaces and submit. | Trimmed duplicates rejected. |
| LOC-07 | Browser | Dallas, Texas → Dallas, TX — Submit aliases that may resolve to identical coordinates. | If coordinates are identical, reject; if provider resolves different points, show those exact points. |
| LOC-08 | Browser | Origin A — Enter one character and submit. | Minimum two-character validation. |
| LOC-09 | Browser | Origin "A" repeated 201 times — Paste into the input. | Field caps at 200 characters; never allows an oversized request silently. |
| LOC-10 | Browser | Type Aust then Austin rapidly — Inspect suggestions after pausing about 0.5 seconds. | Debounced matching suggestions; obsolete responses do not replace the latest location. |
| LOC-11 | Browser | A suggestion for Austin, TX — Select a suggestion; submit a trip. | Selected label remains in the field and backend resolves the intended location. |
| LOC-12 | Browser | Dallas, TX ↔ Austin, TX — Click the swap button. | Both fields swap once; no calculation starts automatically. |
| LOC-13 | Browser | Paris, TX versus Paris, France — Enter each with region/country; inspect labels before calculation. | Resolved city/country is visible; do not silently assume an ambiguous city is the intended one. |
| LOC-14 | Browser | Montréal, QC, Canada → Ottawa, ON, Canada — Enter accented city text. | Unicode text works or returns a clear provider limitation; no encoding corruption. |
| LOC-15 | Browser | qzxv-no-such-place-999999 — Try as Origin; inspect the actual geocoding result. | Clear no-location error if none; if fuzzy matching resolves somewhere, record the label instead of assuming gibberish guarantees no result. |
| LOC-16 | Browser | <img src=x onerror=alert(1)> — Enter as a location and try submission. | Displayed as inert text or rejected; no JavaScript execution. Provider match/error may vary. |

## API field validation

| ID | Method | Sample inputs and action | Expected result |
|---|---|---|---|
| VAL-01 | Controlled | Omit origin — Run this isolated serializer check; it does not call providers. Command: `python scripts/manual_checks.py --case VAL-01`. | Rejected with validation errors, not an unhandled exception. |
| VAL-02 | Controlled | Omit destination — Run this isolated serializer check; it does not call providers. Command: `python scripts/manual_checks.py --case VAL-02`. | Rejected with validation errors, not an unhandled exception. |
| VAL-03 | Controlled | Origin null — Run this isolated serializer check; it does not call providers. Command: `python scripts/manual_checks.py --case VAL-03`. | Rejected with validation errors, not an unhandled exception. |
| VAL-04 | Controlled | Origin 201 characters — Run this isolated serializer check; it does not call providers. Command: `python scripts/manual_checks.py --case VAL-04`. | Rejected with validation errors, not an unhandled exception. |
| VAL-05 | Controlled | Origin exactly 200 characters — Run this isolated serializer check; it does not call providers. Command: `python scripts/manual_checks.py --case VAL-05`. | Accepted by validation; routing availability is a separate check. |
| VAL-06 | Controlled | Whitespace around valid locations — Run this isolated serializer check; it does not call providers. Command: `python scripts/manual_checks.py --case VAL-06`. | Accepted by validation; routing availability is a separate check. |
| VAL-07 | Controlled | Case-insensitive duplicate locations — Run this isolated serializer check; it does not call providers. Command: `python scripts/manual_checks.py --case VAL-07`. | Rejected with validation errors, not an unhandled exception. |
| VAL-08 | Controlled | Unsupported interval 20 — Run this isolated serializer check; it does not call providers. Command: `python scripts/manual_checks.py --case VAL-08`. | Rejected with validation errors, not an unhandled exception. |
| VAL-09 | Controlled | Omit interval — Run this isolated serializer check; it does not call providers. Command: `python scripts/manual_checks.py --case VAL-09`. | Accepted by validation; routing availability is a separate check. |
| VAL-10 | Controlled | Interval null — Run this isolated serializer check; it does not call providers. Command: `python scripts/manual_checks.py --case VAL-10`. | Rejected with validation errors, not an unhandled exception. |

## Load input limits

| ID | Method | Sample inputs and action | Expected result |
|---|---|---|---|
| INP-01 | Controlled | Cargo 0 lb — Run this isolated serializer check; it does not call providers. Command: `python scripts/manual_checks.py --case INP-01`. | Rejected with validation errors, not an unhandled exception. |
| INP-02 | Controlled | Cargo -1 lb — Run this isolated serializer check; it does not call providers. Command: `python scripts/manual_checks.py --case INP-02`. | Rejected with validation errors, not an unhandled exception. |
| INP-03 | Controlled | Cargo 0.009 lb — Run this isolated serializer check; it does not call providers. Command: `python scripts/manual_checks.py --case INP-03`. | Rejected with validation errors, not an unhandled exception. |
| INP-04 | Controlled | Cargo 0.01 lb — Run this isolated serializer check; it does not call providers. Command: `python scripts/manual_checks.py --case INP-04`. | Accepted by validation; routing availability is a separate check. |
| INP-05 | Controlled | Cargo 1 lb — Run this isolated serializer check; it does not call providers. Command: `python scripts/manual_checks.py --case INP-05`. | Accepted by validation; routing availability is a separate check. |
| INP-06 | Controlled | Cargo 29999.99 lb — Run this isolated serializer check; it does not call providers. Command: `python scripts/manual_checks.py --case INP-06`. | Accepted by validation; routing availability is a separate check. |
| INP-07 | Controlled | Cargo 30000 lb — Run this isolated serializer check; it does not call providers. Command: `python scripts/manual_checks.py --case INP-07`. | Accepted by validation; routing availability is a separate check. |
| INP-08 | Controlled | Cargo 30000.01 lb — Run this isolated serializer check; it does not call providers. Command: `python scripts/manual_checks.py --case INP-08`. | Accepted by validation; routing availability is a separate check. |
| INP-09 | Controlled | Cargo 40000 lb — Run this isolated serializer check; it does not call providers. Command: `python scripts/manual_checks.py --case INP-09`. | Accepted by validation; routing availability is a separate check. |
| INP-10 | Controlled | Cargo 40000.01 lb — Run this isolated serializer check; it does not call providers. Command: `python scripts/manual_checks.py --case INP-10`. | Accepted by validation; routing availability is a separate check. |
| INP-11 | Controlled | Cargo 200000 lb — Run this isolated serializer check; it does not call providers. Command: `python scripts/manual_checks.py --case INP-11`. | Accepted by validation; routing availability is a separate check. |
| INP-12 | Controlled | Cargo 200000.01 lb — Run this isolated serializer check; it does not call providers. Command: `python scripts/manual_checks.py --case INP-12`. | Rejected with validation errors, not an unhandled exception. |
| INP-13 | Controlled | Cargo 'abc' lb — Run this isolated serializer check; it does not call providers. Command: `python scripts/manual_checks.py --case INP-13`. | Rejected with validation errors, not an unhandled exception. |
| INP-14 | Controlled | Cargo 'NaN' lb — Run this isolated serializer check; it does not call providers. Command: `python scripts/manual_checks.py --case INP-14`. | Rejected with validation errors, not an unhandled exception. |
| INP-15 | Controlled | Cargo 'Infinity' lb — Run this isolated serializer check; it does not call providers. Command: `python scripts/manual_checks.py --case INP-15`. | Rejected with validation errors, not an unhandled exception. |
| INP-16 | Controlled | Cargo None lb — Run this isolated serializer check; it does not call providers. Command: `python scripts/manual_checks.py --case INP-16`. | Rejected with validation errors, not an unhandled exception. |
| INP-17 | Controlled | Omit load weight — Run this isolated serializer check; it does not call providers. Command: `python scripts/manual_checks.py --case INP-17`. | Rejected with validation errors, not an unhandled exception. |
| INP-18 | Controlled | Boolean true is not a cargo-weight number — Run this isolated serializer check; it does not call providers. Command: `python scripts/manual_checks.py --case INP-18`. | Rejected with validation errors, not an unhandled exception. |

## Departure and timezones

| ID | Method | Sample inputs and action | Expected result |
|---|---|---|---|
| TIME-01 | Browser | Departure empty — Clear date/time and submit. | Required validation; no calculation. |
| TIME-02 | Browser | Departure 1 minute ago — Choose a past local time and submit. | UI rejects a past departure; the API has a documented five-minute clock-skew allowance. |
| TIME-03 | Browser | Departure tomorrow at 00:30 — Calculate and inspect checkpoint ETAs. | No incorrect day reset when the trip crosses midnight. |
| TIME-04 | Browser | Device timezone Asia/Karachi — Inspect the form label and checkpoint times. | Device timezone is explicit; UTC instants are converted consistently. |
| TIME-05 | Browser | Departure today +16 days — Submit a trip. | Backend rejects a departure beyond 15 days; display validation message. |
| TIME-06 | Browser | Departure +15 days, slider +48h — If a route is returned, inspect coverage and move slider. | Times outside actual returned forecasts are Unknown/unavailable; no fabricated weather or Low fallback. |

## Date validation boundaries

| ID | Method | Sample inputs and action | Expected result |
|---|---|---|---|
| DATE-01 | Controlled | Frozen NOW minus 301 seconds — Run this isolated serializer check; it does not call providers. Command: `python scripts/manual_checks.py --case DATE-01`. | Rejected with validation errors, not an unhandled exception. |
| DATE-02 | Controlled | Frozen NOW minus exactly 300 seconds — Run this isolated serializer check; it does not call providers. Command: `python scripts/manual_checks.py --case DATE-02`. | Accepted by validation; routing availability is a separate check. |
| DATE-03 | Controlled | Frozen NOW minus 299 seconds — Run this isolated serializer check; it does not call providers. Command: `python scripts/manual_checks.py --case DATE-03`. | Accepted by validation; routing availability is a separate check. |
| DATE-04 | Controlled | Frozen NOW — Run this isolated serializer check; it does not call providers. Command: `python scripts/manual_checks.py --case DATE-04`. | Accepted by validation; routing availability is a separate check. |
| DATE-05 | Controlled | Frozen NOW plus exactly 15 days — Run this isolated serializer check; it does not call providers. Command: `python scripts/manual_checks.py --case DATE-05`. | Accepted by validation; routing availability is a separate check. |
| DATE-06 | Controlled | Frozen NOW plus 15 days and 1 second — Run this isolated serializer check; it does not call providers. Command: `python scripts/manual_checks.py --case DATE-06`. | Rejected with validation errors, not an unhandled exception. |
| DATE-07 | Controlled | Naive timestamp 2026-11-06T13:00:00 — Run this isolated serializer check; it does not call providers. Command: `python scripts/manual_checks.py --case DATE-07`. | Rejected with validation errors, not an unhandled exception. |
| DATE-08 | Controlled | Invalid timestamp text — Run this isolated serializer check; it does not call providers. Command: `python scripts/manual_checks.py --case DATE-08`. | Rejected with validation errors, not an unhandled exception. |
| DATE-09 | Controlled | Impossible calendar date 2026-02-30T12:00:00Z — Run this isolated serializer check; it does not call providers. Command: `python scripts/manual_checks.py --case DATE-09`. | Rejected with validation errors, not an unhandled exception. |
| DATE-10 | Controlled | Omit departure — Run this isolated serializer check; it does not call providers. Command: `python scripts/manual_checks.py --case DATE-10`. | Rejected with validation errors, not an unhandled exception. |
| DATE-11 | Controlled | 2026-11-06T18:00:00+05:00 equals 13:00Z — Run this isolated serializer check; it does not call providers. Command: `python scripts/manual_checks.py --case DATE-11`. | Accepted by validation; routing availability is a separate check. |
| DATE-12 | Controlled | Repeated New York hour: 2026-11-01T01:30:00-04:00 and -05:00 — Run the frozen-clock DST check. Command: `python scripts/manual_checks.py --case DATE-12`. | Both explicit offsets accepted; their UTC instants differ by 3,600 seconds. |

## Wind thresholds

| ID | Method | Sample inputs and action | Expected result |
|---|---|---|---|
| WND-01 | Controlled | Wind 0 mph; other weather 0; cargo 10,000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case WND-01`. | Low; complete=true. |
| WND-02 | Controlled | Wind 24.99 mph; other weather 0; cargo 10,000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case WND-02`. | Low; complete=true. |
| WND-03 | Controlled | Wind 25 mph; other weather 0; cargo 10,000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case WND-03`. | Moderate; complete=true. |
| WND-04 | Controlled | Wind 25.01 mph; other weather 0; cargo 10,000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case WND-04`. | Moderate; complete=true. |
| WND-05 | Controlled | Wind 34.99 mph; other weather 0; cargo 10,000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case WND-05`. | Moderate; complete=true. |
| WND-06 | Controlled | Wind 35 mph; other weather 0; cargo 10,000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case WND-06`. | High; complete=true. |
| WND-07 | Controlled | Wind 35.01 mph; other weather 0; cargo 10,000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case WND-07`. | High; complete=true. |
| WND-08 | Controlled | Wind 44.99 mph; other weather 0; cargo 10,000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case WND-08`. | High; complete=true. |
| WND-09 | Controlled | Wind 45 mph; other weather 0; cargo 10,000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case WND-09`. | Severe; complete=true. |
| WND-10 | Controlled | Wind 45.01 mph; other weather 0; cargo 10,000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case WND-10`. | Severe; complete=true. |
| WND-11 | Controlled | Wind 54.99 mph; other weather 0; cargo 10,000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case WND-11`. | Severe; complete=true. |
| WND-12 | Controlled | Wind 55 mph; other weather 0; cargo 10,000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case WND-12`. | No Travel; complete=true. |
| WND-13 | Controlled | Wind 55.01 mph; other weather 0; cargo 10,000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case WND-13`. | No Travel; complete=true. |

## Rain thresholds

| ID | Method | Sample inputs and action | Expected result |
|---|---|---|---|
| RAN-01 | Controlled | Rain 0 in/hr; other weather 0; cargo 10,000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case RAN-01`. | Low; complete=true. |
| RAN-02 | Controlled | Rain 0.099 in/hr; other weather 0; cargo 10,000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case RAN-02`. | Low; complete=true. |
| RAN-03 | Controlled | Rain 0.1 in/hr; other weather 0; cargo 10,000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case RAN-03`. | Moderate; complete=true. |
| RAN-04 | Controlled | Rain 0.101 in/hr; other weather 0; cargo 10,000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case RAN-04`. | Moderate; complete=true. |
| RAN-05 | Controlled | Rain 0.249 in/hr; other weather 0; cargo 10,000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case RAN-05`. | Moderate; complete=true. |
| RAN-06 | Controlled | Rain 0.25 in/hr; other weather 0; cargo 10,000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case RAN-06`. | High; complete=true. |
| RAN-07 | Controlled | Rain 0.251 in/hr; other weather 0; cargo 10,000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case RAN-07`. | High; complete=true. |
| RAN-08 | Controlled | Rain 0.499 in/hr; other weather 0; cargo 10,000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case RAN-08`. | High; complete=true. |
| RAN-09 | Controlled | Rain 0.5 in/hr; other weather 0; cargo 10,000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case RAN-09`. | Severe; complete=true. |
| RAN-10 | Controlled | Rain 0.501 in/hr; other weather 0; cargo 10,000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case RAN-10`. | Severe; complete=true. |
| RAN-11 | Controlled | Rain 0.999 in/hr; other weather 0; cargo 10,000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case RAN-11`. | Severe; complete=true. |
| RAN-12 | Controlled | Rain 1.0 in/hr; other weather 0; cargo 10,000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case RAN-12`. | Severe; complete=true. |
| RAN-13 | Controlled | Rain 1.001 in/hr; other weather 0; cargo 10,000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case RAN-13`. | No Travel; complete=true. |

## Snow thresholds

| ID | Method | Sample inputs and action | Expected result |
|---|---|---|---|
| SNW-01 | Controlled | Snow 0 in/hr; other weather 0; cargo 10,000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case SNW-01`. | Low; complete=true. |
| SNW-02 | Controlled | Snow 0.499 in/hr; other weather 0; cargo 10,000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case SNW-02`. | Low; complete=true. |
| SNW-03 | Controlled | Snow 0.5 in/hr; other weather 0; cargo 10,000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case SNW-03`. | Moderate; complete=true. |
| SNW-04 | Controlled | Snow 0.501 in/hr; other weather 0; cargo 10,000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case SNW-04`. | Moderate; complete=true. |
| SNW-05 | Controlled | Snow 0.999 in/hr; other weather 0; cargo 10,000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case SNW-05`. | Moderate; complete=true. |
| SNW-06 | Controlled | Snow 1.0 in/hr; other weather 0; cargo 10,000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case SNW-06`. | High; complete=true. |
| SNW-07 | Controlled | Snow 1.001 in/hr; other weather 0; cargo 10,000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case SNW-07`. | High; complete=true. |
| SNW-08 | Controlled | Snow 1.999 in/hr; other weather 0; cargo 10,000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case SNW-08`. | High; complete=true. |
| SNW-09 | Controlled | Snow 2.0 in/hr; other weather 0; cargo 10,000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case SNW-09`. | Severe; complete=true. |
| SNW-10 | Controlled | Snow 2.001 in/hr; other weather 0; cargo 10,000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case SNW-10`. | Severe; complete=true. |
| SNW-11 | Controlled | Snow 2.999 in/hr; other weather 0; cargo 10,000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case SNW-11`. | Severe; complete=true. |
| SNW-12 | Controlled | Snow 3.0 in/hr; other weather 0; cargo 10,000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case SNW-12`. | Severe; complete=true. |
| SNW-13 | Controlled | Snow 3.001 in/hr; other weather 0; cargo 10,000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case SNW-13`. | No Travel; complete=true. |

## Cargo wind overrides

| ID | Method | Sample inputs and action | Expected result |
|---|---|---|---|
| LDR-01 | Controlled | Wind 50 mph; cargo 29999.99 lb; rain/snow 0 — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case LDR-01`. | Severe; complete=true. |
| LDR-02 | Controlled | Wind 50 mph; cargo 30000 lb; rain/snow 0 — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case LDR-02`. | Severe; complete=true. |
| LDR-03 | Controlled | Wind 50 mph; cargo 30000.01 lb; rain/snow 0 — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case LDR-03`. | No Travel; complete=true. |
| LDR-04 | Controlled | Wind 50 mph; cargo 30001 lb; rain/snow 0 — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case LDR-04`. | No Travel; complete=true. |
| LDR-05 | Controlled | Wind 40 mph; cargo 39999.99 lb; rain/snow 0 — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case LDR-05`. | High; complete=true. |
| LDR-06 | Controlled | Wind 40 mph; cargo 40000 lb; rain/snow 0 — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case LDR-06`. | High; complete=true. |
| LDR-07 | Controlled | Wind 40 mph; cargo 40000.01 lb; rain/snow 0 — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case LDR-07`. | Severe; complete=true. |
| LDR-08 | Controlled | Wind 40 mph; cargo 40001 lb; rain/snow 0 — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case LDR-08`. | Severe; complete=true. |
| LDR-09 | Controlled | Wind 35 mph; cargo 40001 lb; rain/snow 0 — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case LDR-09`. | Severe; complete=true. |
| LDR-10 | Controlled | Wind 44.99 mph; cargo 40001 lb; rain/snow 0 — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case LDR-10`. | Severe; complete=true. |
| LDR-11 | Controlled | Wind 45 mph; cargo 30000 lb; rain/snow 0 — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case LDR-11`. | Severe; complete=true. |
| LDR-12 | Controlled | Wind 45 mph; cargo 30001 lb; rain/snow 0 — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case LDR-12`. | No Travel; complete=true. |
| LDR-13 | Controlled | Wind 54.99 mph; cargo 30001 lb; rain/snow 0 — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case LDR-13`. | No Travel; complete=true. |
| LDR-14 | Controlled | Wind 55 mph; cargo 0.01 lb; rain/snow 0 — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case LDR-14`. | No Travel; complete=true. |
| LDR-15 | Controlled | Wind 55 mph; cargo 30000 lb; rain/snow 0 — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case LDR-15`. | No Travel; complete=true. |
| LDR-16 | Controlled | Wind 55 mph; cargo 200000 lb; rain/snow 0 — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case LDR-16`. | No Travel; complete=true. |
| LDR-17 | Controlled | Wind 34.99 mph; cargo 200000 lb; rain/snow 0 — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case LDR-17`. | Moderate; complete=true. |

## Combined weather

| ID | Method | Sample inputs and action | Expected result |
|---|---|---|---|
| MIX-01 | Controlled | Wind 25; rain 0.25; snow 0; cargo 10000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case MIX-01`. | High; complete=true. |
| MIX-02 | Controlled | Wind 35; rain 0.1; snow 2; cargo 10000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case MIX-02`. | Severe; complete=true. |
| MIX-03 | Controlled | Wind 40; rain 1.01; snow 0; cargo 45000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case MIX-03`. | No Travel; complete=true. |
| MIX-04 | Controlled | Wind 0; rain 0; snow 3.01; cargo 10000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case MIX-04`. | No Travel; complete=true. |
| MIX-05 | Controlled | Wind 0; rain 0; snow 0; cargo 35000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case MIX-05`. | Low; complete=true. |
| MIX-06 | Controlled | Wind 55; rain 0.5; snow 0; cargo 10000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case MIX-06`. | No Travel; complete=true. |
| MIX-07 | Controlled | Wind 40; rain 0; snow 1; cargo 45000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case MIX-07`. | Severe; complete=true. |
| MIX-08 | Controlled | Wind 45; rain 0.1; snow 0.5; cargo 35000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case MIX-08`. | No Travel; complete=true. |
| MIX-09 | Controlled | Wind 10; rain 1; snow 0; cargo 35000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case MIX-09`. | Severe; complete=true. |
| MIX-10 | Controlled | Wind 10; rain 0; snow 3; cargo 35000 lb — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case MIX-10`. | Severe; complete=true. |

## Missing and invalid weather

| ID | Method | Sample inputs and action | Expected result |
|---|---|---|---|
| MIS-01 | Controlled | wind=None; other weather 0 — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case MIS-01`. | Unknown; complete=false. |
| MIS-02 | Controlled | rain=None; other weather 0 — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case MIS-02`. | Unknown; complete=false. |
| MIS-03 | Controlled | snow=None; other weather 0 — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case MIS-03`. | Unknown; complete=false. |
| MIS-04 | Controlled | wind=-1; other weather 0 — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case MIS-04`. | Unknown; complete=false. |
| MIS-05 | Controlled | rain=-0.1; other weather 0 — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case MIS-05`. | Unknown; complete=false. |
| MIS-06 | Controlled | snow=-0.1; other weather 0 — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case MIS-06`. | Unknown; complete=false. |
| MIS-07 | Controlled | wind='bad'; other weather 0 — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case MIS-07`. | Unknown; complete=false. |
| MIS-08 | Controlled | wind='$nan'; other weather 0 — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case MIS-08`. | Unknown; complete=false. |
| MIS-09 | Controlled | wind='$inf'; other weather 0 — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case MIS-09`. | Unknown; complete=false. |
| MIS-10 | Controlled | wind=True; other weather 0 — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case MIS-10`. | Unknown; complete=false. |
| MIS-11 | Controlled | Wind 55; rain missing; snow 0 — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case MIS-11`. | No Travel; complete=false. |
| MIS-12 | Controlled | Wind missing; rain 1.01; snow 0 — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case MIS-12`. | No Travel; complete=false. |
| MIS-13 | Controlled | Entire weather object is missing — Run the controlled check. Command: `python scripts/manual_checks.py --case MIS-13`. | Unknown; incomplete; never Low. |
| MIS-14 | Controlled | Boolean false wind must not become numeric zero — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case MIS-14`. | Unknown; complete=false. |
| MIS-15 | Controlled | String rain "0.10" is invalid provider data — Run this case with the isolated command. Command: `python scripts/manual_checks.py --case MIS-15`. | Unknown; complete=false. |

## Checkpoints and ETAs

| ID | Method | Sample inputs and action | Expected result |
|---|---|---|---|
| GEO-01 | Controlled | 117 miles; 10-mi interval — Run the synthetic road-geometry calculation. Command: `python scripts/manual_checks.py --case GEO-01`. | Checkpoint miles exactly [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 117]; origin/destination included. |
| GEO-02 | Controlled | 117 miles; 25-mi interval — Run the synthetic road-geometry calculation. Command: `python scripts/manual_checks.py --case GEO-02`. | Checkpoint miles exactly [0, 25, 50, 75, 100, 117]; origin/destination included. |
| GEO-03 | Controlled | 117 miles; 50-mi interval — Run the synthetic road-geometry calculation. Command: `python scripts/manual_checks.py --case GEO-03`. | Checkpoint miles exactly [0, 50, 100, 117]; origin/destination included. |
| GEO-04 | Controlled | 50 miles; 25-mi interval — Run the synthetic road-geometry calculation. Command: `python scripts/manual_checks.py --case GEO-04`. | Checkpoint miles exactly [0, 25, 50]; origin/destination included. |
| GEO-05 | Controlled | 7 miles; 25-mi interval — Run the synthetic road-geometry calculation. Command: `python scripts/manual_checks.py --case GEO-05`. | Checkpoint miles exactly [0, 7]; origin/destination included. |
| GEO-06 | Controlled | 25.01 miles; 25-mi interval — Run the synthetic road-geometry calculation. Command: `python scripts/manual_checks.py --case GEO-06`. | Checkpoint miles exactly [0, 25, 25.01]; origin/destination included. |
| GEO-07 | Controlled | 117 miles; 25-mi interval; total duration 11,700 seconds — Inspect second checkpoint ETA offset. Command: `python scripts/manual_checks.py --case GEO-07`. | Mile 25 arrives 2,500 seconds after departure; destination offset 11,700 seconds. |
| GEO-08 | Controlled | Start 2026-11-06 23:00 UTC; duration 11,700 seconds — Inspect destination timestamp. Command: `python scripts/manual_checks.py --case GEO-08`. | Arrival 2026-11-07T02:15:00+00:00. |
| GEO-09 | Controlled | Road bends through [1,0] before [1,1] — Inspect a checkpoint at 75% distance and preserved road vertices. Command: `python scripts/manual_checks.py --case GEO-09`. | Longitude near 1 at 75%; slices retain the bend, not a straight origin/destination shortcut. |
| GEO-10 | Controlled | Geometry [179,10] → [-179,10] — Run antimeridian interpolation. Command: `python scripts/manual_checks.py --case GEO-10`. | Midpoint absolute longitude near 180, not 0. |
| GEO-11 | Controlled | {"coordinates": []} — Run malformed provider-geometry scenario. Command: `python scripts/manual_checks.py --case GEO-11`. | Reject unusable data; no fabricated geometry or ETA. |
| GEO-12 | Controlled | {"coordinates": [[0, 0], [0, 0]]} — Run malformed provider-geometry scenario. Command: `python scripts/manual_checks.py --case GEO-12`. | Reject unusable data; no fabricated geometry or ETA. |
| GEO-13 | Controlled | {"coordinates": [[181, 0], [0, 0]]} — Run malformed provider-geometry scenario. Command: `python scripts/manual_checks.py --case GEO-13`. | Reject unusable data; no fabricated geometry or ETA. |
| GEO-14 | Controlled | {"miles": 0} — Run malformed provider-geometry scenario. Command: `python scripts/manual_checks.py --case GEO-14`. | Reject unusable data; no fabricated geometry or ETA. |
| GEO-15 | Controlled | {"duration": 0} — Run malformed provider-geometry scenario. Command: `python scripts/manual_checks.py --case GEO-15`. | Reject unusable data; no fabricated geometry or ETA. |
| GEO-16 | Controlled | {"interval": 20} — Run malformed provider-geometry scenario. Command: `python scripts/manual_checks.py --case GEO-16`. | Reject unusable data; no fabricated geometry or ETA. |

## Distance-weighted summaries

| ID | Method | Sample inputs and action | Expected result |
|---|---|---|---|
| SUM-01 | Controlled | [[0, 'Low'], [25, 'Low'], [50, 'High'], [67, 'Severe']] — Run the endpoint-to-segment calculation. Command: `python scripts/manual_checks.py --case SUM-01`. | 25 Low mi + 25 High mi + 17 Severe mi; average 101/67. |
| SUM-02 | Controlled | [[0, 'Low'], [25, 'High'], [50, 'Low']] — Run the endpoint-to-segment calculation. Command: `python scripts/manual_checks.py --case SUM-02`. | Both intervals take the High endpoint; 50 High miles. |
| SUM-03 | Controlled | [[0, 'Low'], [25, 'Unknown', False], [50, 'Low']] — Run the endpoint-to-segment calculation. Command: `python scripts/manual_checks.py --case SUM-03`. | 50 Unknown miles; average null; ineligible. |
| SUM-04 | Controlled | [[0, 'Low'], [25, 'Low'], [50, 'Unknown', False]] — Run the endpoint-to-segment calculation. Command: `python scripts/manual_checks.py --case SUM-04`. | Coverage 50%; average null, not a safe-looking partial average. |
| SUM-05 | Controlled | [[0, 'Low'], [25, 'No Travel']] — Run the endpoint-to-segment calculation. Command: `python scripts/manual_checks.py --case SUM-05`. | 25 No Travel miles; excluded. |
| SUM-06 | Controlled | [[0, 'Unknown', False], [25, 'No Travel']] — Run the endpoint-to-segment calculation. Command: `python scripts/manual_checks.py --case SUM-06`. | Known No Travel preserved despite missing adjacent weather. |
| SUM-07 | Controlled | [[0, 'Low'], [7, 'Severe']] — Run the endpoint-to-segment calculation. Command: `python scripts/manual_checks.py --case SUM-07`. | Final partial segment contributes 7 miles, not a full 25. |
| SUM-08 | Controlled | [[0, 'Low'], [25, 'Low']] — Run the endpoint-to-segment calculation. Command: `python scripts/manual_checks.py --case SUM-08`. | Complete weather but unsupported truck mode remains ineligible. |
| SUM-09 | Controlled | 117 miles; uniform High risk; interval 10 — Run uniform-risk summary at this interval. Command: `python scripts/manual_checks.py --case SUM-09`. | 117 High miles; average 2; total miles remain 117. |
| SUM-10 | Controlled | 117 miles; uniform High risk; interval 25 — Run uniform-risk summary at this interval. Command: `python scripts/manual_checks.py --case SUM-10`. | 117 High miles; average 2; total miles remain 117. |
| SUM-11 | Controlled | 117 miles; uniform High risk; interval 50 — Run uniform-risk summary at this interval. Command: `python scripts/manual_checks.py --case SUM-11`. | 117 High miles; average 2; total miles remain 117. |

## Recommendation order

| ID | Method | Sample inputs and action | Expected result |
|---|---|---|---|
| RNK-01 | Controlled | [{"id": "A", "severe": 1, "high": 90, "average": 2, "duration": 9000}, {"id": "B", "severe": 2, "duration": 100}] — Run the ranking scenario. Command: `python scripts/manual_checks.py --case RNK-01`. | Fewer Severe miles wins even with more High miles and longer duration. |
| RNK-02 | Controlled | [{"id": "A", "high": 1, "average": 2, "duration": 9000}, {"id": "B", "high": 2, "average": 1, "duration": 100}] — Run the ranking scenario. Command: `python scripts/manual_checks.py --case RNK-02`. | With equal Severe miles, fewer High miles wins. |
| RNK-03 | Controlled | [{"id": "A", "average": 0.5, "duration": 9000}, {"id": "B", "average": 1, "duration": 100}] — Run the ranking scenario. Command: `python scripts/manual_checks.py --case RNK-03`. | Equal Severe/High miles: lower average wins. |
| RNK-04 | Controlled | [{"id": "A", "duration": 500}, {"id": "B", "duration": 600}] — Run the ranking scenario. Command: `python scripts/manual_checks.py --case RNK-04`. | Equal risk metrics: shorter duration wins. |
| RNK-05 | Controlled | [{"id": "B"}, {"id": "A"}] — Run the ranking scenario. Command: `python scripts/manual_checks.py --case RNK-05`. | Exact tie breaks deterministically by route ID. |
| RNK-06 | Controlled | [{"id": "unsafe", "eligible": false, "blocked": true}, {"id": "safe", "severe": 20}] — Run the ranking scenario. Command: `python scripts/manual_checks.py --case RNK-06`. | No Travel route cannot win by having fewer Severe miles. |
| RNK-07 | Controlled | [{"id": "unknown", "eligible": false}, {"id": "safe", "high": 50}] — Run the ranking scenario. Command: `python scripts/manual_checks.py --case RNK-07`. | Incomplete weather cannot beat a fully covered route. |
| RNK-08 | Controlled | [{"id": "A", "eligible": false, "blocked": true}, {"id": "B", "eligible": false, "blocked": true}] — Run the ranking scenario. Command: `python scripts/manual_checks.py --case RNK-08`. | No safe route available; do not recommend a least-bad unsafe route. |
| RNK-09 | Controlled | [{"id": "A", "eligible": false}, {"id": "B", "eligible": false, "blocked": true}] — Run the ranking scenario. Command: `python scripts/manual_checks.py --case RNK-09`. | Mixed incomplete/unsafe options also yield no recommendation. |
| RNK-10 | Controlled | [{"id": "only"}] — Run the ranking scenario. Command: `python scripts/manual_checks.py --case RNK-10`. | One eligible route can be recommended; no need to invent alternatives. |

## Routing provider alternatives

| ID | Method | Sample inputs and action | Expected result |
|---|---|---|---|
| RTE-01 | Controlled | one — Run the isolated TomTom-response scenario. Command: `python scripts/manual_checks.py --case RTE-01`. | One actual option plus a fewer-alternatives warning. |
| RTE-02 | Controlled | two — Run the isolated TomTom-response scenario. Command: `python scripts/manual_checks.py --case RTE-02`. | Two distinct options, no fake third route. |
| RTE-03 | Controlled | three — Run the isolated TomTom-response scenario. Command: `python scripts/manual_checks.py --case RTE-03`. | Main route plus two alternatives, requested in truck mode. |
| RTE-04 | Controlled | duplicate — Run the isolated TomTom-response scenario. Command: `python scripts/manual_checks.py --case RTE-04`. | Identical alternatives deduplicated. |
| RTE-05 | Controlled | empty — Run the isolated TomTom-response scenario. Command: `python scripts/manual_checks.py --case RTE-05`. | No-route error; no risk calculations on invented geometry. |
| RTE-06 | Controlled | invalid_geometry — Run the isolated TomTom-response scenario. Command: `python scripts/manual_checks.py --case RTE-06`. | Unusable route omitted; no usable routes remain. |
| RTE-07 | Controlled | invalid_duration — Run the isolated TomTom-response scenario. Command: `python scripts/manual_checks.py --case RTE-07`. | Missing/zero ETA route omitted. |
| RTE-08 | Controlled | mixed_invalid — Run the isolated TomTom-response scenario. Command: `python scripts/manual_checks.py --case RTE-08`. | Keep usable route and explain omitted malformed alternative. |
| RTE-09 | Controlled | nontruck — Run the isolated TomTom-response scenario. Command: `python scripts/manual_checks.py --case RTE-09`. | Non-truck section disclosed; downstream eligibility must be false. |
| RTE-10 | Controlled | three — Run the isolated TomTom-response scenario. Command: `python scripts/manual_checks.py --case RTE-10`. | 30,000 lb cargo + 18,000 lb empty weight converts upward to 21,773 kg. |
| RTE-11 | Controlled | Origin and destination resolve to identical coordinates — Run same-coordinate routing guard. Command: `python scripts/manual_checks.py --case RTE-11`. | 422 same_location before a routing request. |

## Geocoding response handling

| ID | Method | Sample inputs and action | Expected result |
|---|---|---|---|
| GCD-01 | Controlled | valid — Run the isolated geocoder response. Command: `python scripts/manual_checks.py --case GCD-01`. | Human-readable address resolves to GeoJSON longitude/latitude order. |
| GCD-02 | Controlled | empty — Run the isolated geocoder response. Command: `python scripts/manual_checks.py --case GCD-02`. | No geocoding results produce a clear 422. |
| GCD-03 | Controlled | invalid_position — Run the isolated geocoder response. Command: `python scripts/manual_checks.py --case GCD-03`. | Out-of-range latitude is not used in routing. |
| GCD-04 | Controlled | malformed — Run the isolated geocoder response. Command: `python scripts/manual_checks.py --case GCD-04`. | Malformed geocoder coordinates produce a provider error. |
| GCD-05 | Controlled | cache — Run the isolated geocoder response. Command: `python scripts/manual_checks.py --case GCD-05`. | Repeated equivalent search uses cached provider results. |
| GCD-06 | Controlled | encoded — Run the isolated geocoder response. Command: `python scripts/manual_checks.py --case GCD-06`. | Slash, question mark, and angle brackets are encoded as query text, not API path/query injection. |

## Weather normalization

| ID | Method | Sample inputs and action | Expected result |
|---|---|---|---|
| WTH-01 | Controlled | 80.4672 km/h → 50 mph; 2.54 mm rain + 2.54 mm showers → 0.2 in; 2.54 cm snow → 1 in. — Run the controlled normalization scenario. Command: `python scripts/manual_checks.py --case WTH-01`. | 80.4672 km/h → 50 mph; 2.54 mm rain + 2.54 mm showers → 0.2 in; 2.54 cm snow → 1 in. |
| WTH-02 | Controlled | Imperial values preserved; rainfall includes showers. — Run the controlled normalization scenario. Command: `python scripts/manual_checks.py --case WTH-02`. | Imperial values preserved; rainfall includes showers. |
| WTH-03 | Controlled | Missing snowfall stays null, not zero. — Run the controlled normalization scenario. Command: `python scripts/manual_checks.py --case WTH-03`. | Missing snowfall stays null, not zero. |
| WTH-04 | Controlled | Negative provider rain becomes unavailable. — Run the controlled normalization scenario. Command: `python scripts/manual_checks.py --case WTH-04`. | Negative provider rain becomes unavailable. |
| WTH-05 | Controlled | Unsupported snowfall unit rejected. — Run the controlled normalization scenario. Command: `python scripts/manual_checks.py --case WTH-05`. | Unsupported snowfall unit rejected. |
| WTH-06 | Controlled | Irregular hourly timeline rejected. — Run the controlled normalization scenario. Command: `python scripts/manual_checks.py --case WTH-06`. | Irregular hourly timeline rejected. |
| WTH-07 | Controlled | Misaligned arrays rejected. — Run the controlled normalization scenario. Command: `python scripts/manual_checks.py --case WTH-07`. | Misaligned arrays rejected. |
| WTH-08 | Controlled | Hourly winds [10,30,55]; target offset 0 seconds — Run timestamp selection. Command: `python scripts/manual_checks.py --case WTH-08`. | Select wind 10 mph from the interval ending at/after the target time. |
| WTH-09 | Controlled | Hourly winds [10,30,55]; target offset 1 seconds — Run timestamp selection. Command: `python scripts/manual_checks.py --case WTH-09`. | Select wind 30 mph from the interval ending at/after the target time. |
| WTH-10 | Controlled | Hourly winds [10,30,55]; target offset 3600 seconds — Run timestamp selection. Command: `python scripts/manual_checks.py --case WTH-10`. | Select wind 30 mph from the interval ending at/after the target time. |
| WTH-11 | Controlled | Hourly winds [10,30,55]; target offset 3601 seconds — Run timestamp selection. Command: `python scripts/manual_checks.py --case WTH-11`. | Select wind 55 mph from the interval ending at/after the target time. |
| WTH-12 | Controlled | Hourly winds [10,30,55]; target offset -1 seconds — Run timestamp selection. Command: `python scripts/manual_checks.py --case WTH-12`. | Unavailable outside the horizon. |
| WTH-13 | Controlled | Hourly winds [10,30,55]; target offset 7201 seconds — Run timestamp selection. Command: `python scripts/manual_checks.py --case WTH-13`. | Unavailable outside the horizon. |
| WTH-14 | Controlled | deduplicate — Run the batched/cache scenario. Command: `python scripts/manual_checks.py --case WTH-14`. | Repeated coordinates reuse one request/cache entry. |
| WTH-15 | Controlled | batch — Run the batched/cache scenario. Command: `python scripts/manual_checks.py --case WTH-15`. | 51 coordinates are requested in three batches of at most 25. |
| WTH-16 | Controlled | failure — Run the batched/cache scenario. Command: `python scripts/manual_checks.py --case WTH-16`. | Provider failure yields unavailable weather and warnings. |
| WTH-17 | Controlled | wrong_count — Run the batched/cache scenario. Command: `python scripts/manual_checks.py --case WTH-17`. | Wrong number of provider locations is not silently assigned to checkpoints. |
| WTH-18 | Controlled | limit — Run the batched/cache scenario. Command: `python scripts/manual_checks.py --case WTH-18`. | Over-limit sample counts return an explicit sampling-limit error. |
| WTH-19 | Controlled | 10 m/s is normalized to approximately 22.3694 mph. — Run isolated unit/schema handling. Command: `python scripts/manual_checks.py --case WTH-19`. | 10 m/s is normalized to approximately 22.3694 mph. |
| WTH-20 | Controlled | 10 knots is normalized to approximately 11.5078 mph. — Run isolated unit/schema handling. Command: `python scripts/manual_checks.py --case WTH-20`. | 10 knots is normalized to approximately 11.5078 mph. |
| WTH-21 | Controlled | 25.4 mm snowfall depth is normalized to 1 inch. — Run isolated unit/schema handling. Command: `python scripts/manual_checks.py --case WTH-21`. | 25.4 mm snowfall depth is normalized to 1 inch. |
| WTH-22 | Controlled | An empty forecast timeline is unavailable, not safe weather. — Run isolated unit/schema handling. Command: `python scripts/manual_checks.py --case WTH-22`. | An empty forecast timeline is unavailable, not safe weather. |
| WTH-23 | Controlled | Unexpected non-Unix time metadata is rejected. — Run isolated unit/schema handling. Command: `python scripts/manual_checks.py --case WTH-23`. | Unexpected non-Unix time metadata is rejected. |
| WTH-24 | Controlled | A missing required hourly variable is rejected. — Run isolated unit/schema handling. Command: `python scripts/manual_checks.py --case WTH-24`. | A missing required hourly variable is rejected. |

## Provider transport failures

| ID | Method | Sample inputs and action | Expected result |
|---|---|---|---|
| ERR-01 | Controlled | timeout — Simulate only this provider failure; no real API request. Command: `python scripts/manual_checks.py --case ERR-01`. | Friendly structured error; HTTP-equivalent status 504; no key or raw request URL exposed. |
| ERR-02 | Controlled | connection — Simulate only this provider failure; no real API request. Command: `python scripts/manual_checks.py --case ERR-02`. | Friendly structured error; HTTP-equivalent status 502; no key or raw request URL exposed. |
| ERR-03 | Controlled | rate_limit — Simulate only this provider failure; no real API request. Command: `python scripts/manual_checks.py --case ERR-03`. | Friendly structured error; HTTP-equivalent status 429; no key or raw request URL exposed. |
| ERR-04 | Controlled | unauthorized — Simulate only this provider failure; no real API request. Command: `python scripts/manual_checks.py --case ERR-04`. | Friendly structured error; HTTP-equivalent status 503; no key or raw request URL exposed. |
| ERR-05 | Controlled | forbidden — Simulate only this provider failure; no real API request. Command: `python scripts/manual_checks.py --case ERR-05`. | Friendly structured error; HTTP-equivalent status 503; no key or raw request URL exposed. |
| ERR-06 | Controlled | server_error — Simulate only this provider failure; no real API request. Command: `python scripts/manual_checks.py --case ERR-06`. | Friendly structured error; HTTP-equivalent status 502; no key or raw request URL exposed. |
| ERR-07 | Controlled | invalid_json — Simulate only this provider failure; no real API request. Command: `python scripts/manual_checks.py --case ERR-07`. | Friendly structured error; HTTP-equivalent status 502; no key or raw request URL exposed. |
| ERR-08 | Controlled | invalid_shape — Simulate only this provider failure; no real API request. Command: `python scripts/manual_checks.py --case ERR-08`. | Friendly structured error; HTTP-equivalent status 502; no key or raw request URL exposed. |

## Complete controlled pipeline

| ID | Method | Sample inputs and action | Expected result |
|---|---|---|---|
| FLOW-01 | Controlled | safe — Run the isolated route/weather pipeline. Command: `python scripts/manual_checks.py --case FLOW-01`. | Three eligible routes and a deterministic recommendation. |
| FLOW-02 | Controlled | unsafe — Run the isolated route/weather pipeline. Command: `python scripts/manual_checks.py --case FLOW-02`. | All routes No Travel; no recommendation. |
| FLOW-03 | Controlled | missing — Run the isolated route/weather pipeline. Command: `python scripts/manual_checks.py --case FLOW-03`. | Missing weather cannot become Low or a safe recommendation. |
| FLOW-04 | Controlled | nontruck — Run the isolated route/weather pipeline. Command: `python scripts/manual_checks.py --case FLOW-04`. | A returned non-truck section prevents a recommendation. |
| FLOW-05 | Controlled | slider — Run the isolated route/weather pipeline. Command: `python scripts/manual_checks.py --case FLOW-05`. | Slider +48h changes selected-hour weather while route arrival risk/recommendation stays unchanged. |
| FLOW-06 | Controlled | horizon — Run the isolated route/weather pipeline. Command: `python scripts/manual_checks.py --case FLOW-06`. | Arrival outside forecast timestamps stays incomplete. |

## HTTP API contract

| ID | Method | Sample inputs and action | Expected result |
|---|---|---|---|
| API-01 | Controlled | GET /api/health/; {} — Run this isolated HTTP-handler check. Command: `python scripts/manual_checks.py --case API-01`. | HTTP 200; JSON response for registered API endpoints. |
| API-02 | Controlled | GET /api/routes/calculate/; {} — Run this isolated HTTP-handler check. Command: `python scripts/manual_checks.py --case API-02`. | HTTP 405; JSON response for registered API endpoints. |
| API-03 | Controlled | POST /api/health/; {} — Run this isolated HTTP-handler check. Command: `python scripts/manual_checks.py --case API-03`. | HTTP 405; JSON response for registered API endpoints. |
| API-04 | Controlled | GET /api/places/; {'q': 'A'} — Run this isolated HTTP-handler check. Command: `python scripts/manual_checks.py --case API-04`. | HTTP 400; JSON response for registered API endpoints. |
| API-05 | Controlled | GET /api/places/; {'q': 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'} — Run this isolated HTTP-handler check. Command: `python scripts/manual_checks.py --case API-05`. | HTTP 400; JSON response for registered API endpoints. |
| API-06 | Controlled | GET /api/trips/00000000-0000-0000-0000-000000000000/; {} — Run this isolated HTTP-handler check. Command: `python scripts/manual_checks.py --case API-06`. | HTTP 404; JSON response for registered API endpoints. |
| API-07 | Controlled | GET /api/trips/not-a-uuid/; {} — Run this isolated HTTP-handler check. Command: `python scripts/manual_checks.py --case API-07`. | HTTP 404 for the unmatched UUID URL; the default HTML 404 is acceptable. |
| API-08 | Controlled | GET /api/trips/00000000-0000-0000-0000-000000000000/forecast/; {'hour': -1} — Run this isolated HTTP-handler check. Command: `python scripts/manual_checks.py --case API-08`. | HTTP 400; JSON response for registered API endpoints. |
| API-09 | Controlled | GET /api/trips/00000000-0000-0000-0000-000000000000/forecast/; {'hour': 49} — Run this isolated HTTP-handler check. Command: `python scripts/manual_checks.py --case API-09`. | HTTP 400; JSON response for registered API endpoints. |
| API-10 | Controlled | GET /api/trips/00000000-0000-0000-0000-000000000000/forecast/; {'hour': '1.5'} — Run this isolated HTTP-handler check. Command: `python scripts/manual_checks.py --case API-10`. | HTTP 400; JSON response for registered API endpoints. |
| API-11 | Controlled | GET /api/trips/00000000-0000-0000-0000-000000000000/forecast/; {'hour': 'abc'} — Run this isolated HTTP-handler check. Command: `python scripts/manual_checks.py --case API-11`. | HTTP 400; JSON response for registered API endpoints. |
| API-12 | Controlled | POST incomplete JSON {origin: Dallas, TX} — Run handler validation. Command: `python scripts/manual_checks.py --case API-12`. | HTTP 400 with required field errors. |
| API-13 | Controlled | Valid trip, but key absent in isolated settings — Run the missing-key handler scenario. Command: `python scripts/manual_checks.py --case API-13`. | HTTP 503; error code missing_api_key. |
| API-14 | Controlled | Malformed JSON body — Run malformed JSON submission. Command: `python scripts/manual_checks.py --case API-14`. | HTTP 400, no uncaught server error. |
| API-15 | Controlled | Seeded isolated trip; forecast hour 0 — Request selected-hour forecast from a process-local test trip. Command: `python scripts/manual_checks.py --case API-15`. | HTTP 200; returned hour 0. |
| API-16 | Controlled | Seeded isolated trip; forecast hour 48 — Request selected-hour forecast from a process-local test trip. Command: `python scripts/manual_checks.py --case API-16`. | HTTP 200; returned hour 48. |
| API-17 | Controlled | Seeded isolated trip; forecast hour omitted — Request selected-hour forecast from a process-local test trip. Command: `python scripts/manual_checks.py --case API-17`. | HTTP 200; returned hour 0. |
| API-18 | Controlled | Isolated anonymous throttle reduced to one request/hour — Make two isolated mocked location searches; do not flood the real server. Command: `python scripts/manual_checks.py --case API-18`. | First HTTP 200, second HTTP 429. |
| API-19 | Controlled | POST text/plain to the JSON route endpoint — Run unsupported content-type handler check. Command: `python scripts/manual_checks.py --case API-19`. | HTTP 415 with a clear unsupported-media response. |
| API-20 | Controlled | Forecast hour empty string; parameter is present — Run isolated query validation. Command: `python scripts/manual_checks.py --case API-20`. | HTTP 400; an omitted hour defaults to 0 but an empty explicit hour is invalid. |

## Map and responsive interface

| ID | Method | Sample inputs and action | Expected result |
|---|---|---|---|
| MAP-01 | Browser | Baseline calculated trip — Select each route card. | Selected card, checkpoint table, and highlighted road geometry correspond to the same route. |
| MAP-02 | Browser | Baseline calculated trip — Click a checkpoint on the map. | Panel shows coordinates, mile distance, arrival time, wind, rain, snow, risk and reason. |
| MAP-03 | Browser | Baseline calculated trip — Open Origin, an interior checkpoint, and Destination from the table. | Correct distinct checkpoint details and map position for each. |
| MAP-04 | Browser | Baseline calculated trip — Close checkpoint panel. | Panel closes; map and route selection remain usable. |
| MAP-05 | Browser | Baseline calculated trip — Pan/zoom, then click Fit all routes. | All available alternatives fit; no page freeze or route disappearance. |
| MAP-06 | Browser | Baseline calculated trip — Zoom into bends and compare routes/checkpoints with roads. | Full provider geometry follows roads; no straight-line fabricated routes. |
| MAP-07 | Browser | Baseline calculated trip — Inspect legend, road colors, and checkpoint badges. | Text labels accompany colors; road colors describe arrival-time risk. |
| MAP-08 | Browser | Baseline calculated trip — Inspect each risk bar and detailed summary. | Low+Moderate+High+Severe+No Travel+Unknown miles equal total distance within rounding tolerance. |
| MAP-09 | Browser | Baseline calculated trip — Compare ETA at origin, interior points, destination, and route card. | ETAs increase; destination ETA matches route summary; dates/timezone are explicit. |
| MAP-10 | Browser | Browser width 390 px — Inspect form, cards, map, details and table. | No horizontal page overflow; table itself may scroll horizontally; controls remain accessible. |
| MAP-11 | Browser | Browser width 768 px — Resize from desktop to tablet. | Map resizes correctly; no overlapping or offscreen primary controls. |
| MAP-12 | Browser | Browser width 1440 px — Inspect three routes when actually available. | Readable cards; map retains useful area; labels and metrics are not clipped. |
| MAP-13 | Browser | Keyboard only — Tab through form, interval buttons, calculate, cards and checkpoint table. | Visible focus; primary actions work with Enter/Space; record inaccessible controls as failures. |
| MAP-14 | Browser | Risk rules dialog — Open rules, inspect values, close it; try Escape and keyboard focus. | Displayed rules match thresholds. Escape/focus should support an accessible dialog; record any unsupported behavior rather than skipping it. |
| MAP-15 | Browser | Zoom browser to 200% — Inspect controls and details. | Readable content, usable scrolling, no loss of essential actions. |
| MAP-16 | Browser | Console and Network panels — Perform one normal calculation and inspect errors. | No uncaught page errors or exposed API keys; provider failures appear as clear app messages. |
| MAP-17 | Browser | Viewport 360 px wide — Inspect form, results, map and details at this width. | No horizontal page overflow; essential controls remain usable. |
| MAP-18 | Browser | Viewport 320 px wide — Inspect a small-phone layout and try primary controls. | No horizontal page overflow or lost primary controls; record any current minimum-width limitation as a failure. |

## Forecast slider and corridor

| ID | Method | Sample inputs and action | Expected result |
|---|---|---|---|
| SLD-01 | Browser | Before any trip — Try the slider. | Slider disabled; no meaningless forecast requests. |
| SLD-02 | Browser | Baseline trip; offset 0 — Move to the left endpoint. | Timestamp equals departure; forecast response hour=0. |
| SLD-03 | Browser | Baseline trip; offset 48 — Move to the right endpoint. | Timestamp equals departure plus 48 hours; response hour=48. |
| SLD-04 | Browser | Offsets 1, 12, 24, 36 — Visit each offset and inspect forecast request/timestamp. | Each returned hour and displayed timestamp matches the selection. |
| SLD-05 | Browser | Same checkpoint at 0 then 48 — Compare arrival and corridor sections. | Corridor weather reflects selected time; arrival weather remains fixed. Similar real weather at different hours is valid. |
| SLD-06 | Browser | Recommended trip — Move through several hours. | Recommendation and arrival-risk road segments do not rerank/change because of the slider. |
| SLD-07 | Browser | Weather layer toggle — Toggle off then on. | Corridor heat layer changes visibility; route lines/checkpoints remain visible. |
| SLD-08 | Browser | Slow 3G network; rapidly scrub 0→12→48 — Inspect last forecast response and caption. | Final +48h data wins; stale earlier requests cannot overwrite it. |
| SLD-09 | Browser | Visit 12, then 24, then 12 — Inspect Network panel. | Second visit to 12 uses client cache; no duplicate request for that cached hour. |
| SLD-10 | Browser | Slow network, uncached hour — Move slider and watch loading state. | Do not display previous-hour weather as if it matched the new label; show loading/unavailable state. |
| SLD-11 | Browser | Backend stopped temporarily after trip — Move to an uncached hour; restore backend and retry. | Clear forecast error; retry action works, or trip-expired message requests recalculation after restart. |
| SLD-12 | Browser | A forecast beyond provider horizon — Inspect missing count and checkpoint selected-hour section. | Unknown/unavailable labels; no invented Low-risk heatmap. |
| SLD-13 | Browser | Calculated trip — Toggle layer repeatedly and inspect map smoothness. | No accumulating map instances, duplicate controls, or frozen interaction. |
| SLD-14 | Browser | Trip A, then calculate Trip B — Inspect slider and checkpoint details. | Offset resets to 0; no forecast or checkpoint details from Trip A. |

## Errors and recovery

| ID | Method | Sample inputs and action | Expected result |
|---|---|---|---|
| REC-01 | Browser | Backend stopped; frontend stays open — Stop Django with Ctrl+C; return to tab. | Service offline/connection unavailable; no stale claim of readiness. |
| REC-02 | Browser | Backend restarted with existing valid local key — Restart Django and wait or click Retry connection. | Ready status recovers; trip input text remains intact. |
| REC-03 | Browser | Setup response false→true in a controlled browser test — Run npm.cmd run test:e2e -- --grep "setup\|configuration recheck". | Banner clears automatically or through Check again, without losing draft inputs. |
| REC-04 | Browser | Slow 3G; valid trip — Submit and immediately click Calculate again. | One active submission; button disabled while working. |
| REC-05 | Browser | Slow 3G; valid trip — Submit, then Cancel request. | Loading clears; late response cannot populate a cancelled trip. Server may finish an already-started provider call. |
| REC-06 | Browser | After cancelling — Change destination and calculate. | Only the new trip results appear. |
| REC-07 | Browser | Map requests blocked in DevTools — Block basemaps.cartocdn.com, reload, inspect after up to 20 seconds. | Map failure/retry feedback; form and route results remain usable. Unblock requests afterward. |
| REC-08 | Browser | Internet connection temporarily offline — Use DevTools Offline; try an action; restore Online. | Useful connection error; recovery without blank screen. |
| REC-09 | Browser | An existing calculated trip — Restart Django then request an uncached forecast hour. | 404 trip_expired or clear recalculation prompt; no fabricated forecast. |
| REC-10 | Browser | Configured backend; return to app tab — Switch away and back after backend state changes. | Health rechecked on focus/visibility; display matches current backend. |
| REC-11 | Browser | Existing safe or unsafe real trip — Recalculate with another load, keeping other inputs similar. | Cargo input is sent correctly; changed outcomes are based on actual wind, not an assumption that higher load always changes risk. |

## Performance and submission

| ID | Method | Sample inputs and action | Expected result |
|---|---|---|---|
| OPS-01 | Browser | Dallas, TX → Los Angeles, CA; 10-mi interval — Try one long trip. | Either complete supported analysis or explicit sample-limit/provider error; no silent truncation. |
| OPS-02 | Browser | Same long trip; 50-mi interval — Retry with coarser sampling. | Fewer samples; if still over limit, explain honestly rather than fabricating completion. |
| OPS-03 | Browser | Provider failures or rate limits — Use ERR controlled cases instead of flooding real services. | 429/timeout handling proven without exhausting your live account. |
| OPS-04 | Browser | Production Vercel URL — After deployment, repeat SMK-01/02/03 and SLD-03 on HTTPS. | Frontend/API communication and real forecasts work at the actual hosted URL. Mark Blocked until deployed. |
| OPS-05 | Browser | Production environment configuration — Review provider key and Django settings privately in the host dashboard. | Keys server-side; unique production secret; debug false; exact allowed hostname. No secret values copied into results. |
| OPS-06 | Browser | Repository and built frontend — Inspect tracked filenames, browser requests, and JavaScript assets. | No tracked .env/private key; frontend never sends a TomTom private key directly. |
| OPS-07 | Browser | Trip notes — Read sampling, ETA and truck-configuration disclosures. | Uniform-speed/rest-stop limitations and actual configured vehicle restrictions are clear. |
| OPS-08 | Browser | Submission links — Open GitHub, hosted URL and recorded Loom in a separate session. | Evaluator can access all links. Mark Blocked until published/recorded. |

## Result message to share

```text
Case ID: SLD-08
Status: Fail
Origin / destination: Dallas, TX / Austin, TX
Departure and timezone: [actual selected value and device zone]
Cargo / interval: 35000 lb / 25 mi
Steps: [what you clicked, including network throttling if relevant]
Expected: final +48h forecast wins
Actual: [observed behavior]
Browser and screen width: [example: Chrome, 1440 px]
Screenshot or console/API error: [attach or paste sanitized text]
```

For a controlled case, share the printed JSON and ID. For live cases, include the selected timestamp; forecasts and traffic may differ by the time the issue is investigated. Your CSV remains the record of your manual run; isolated utility output does not silently modify it.
