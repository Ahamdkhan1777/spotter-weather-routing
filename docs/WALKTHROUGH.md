# Walkthrough recording — approximately 8 minutes

Recording status: **not recorded or uploaded**. Loom URL: **not yet available**.

Before recording, configure a real TomTom key, publish the GitHub repository, deploy the app, and verify the live trip flow. This script is preparation, not a substitute for the requested Loom deliverable.

## 0:00–0:40 — Purpose

Open the actual hosted application. Explain that Spotter compares real truck routes using the weather when the truck reaches each checkpoint, with cargo-load overrides. Show the service-ready indicator and name the React/Django stack.

## 0:40–1:40 — Trip inputs

Enter an actual origin and destination and show location suggestions. Set a departure in the supported forecast horizon. Explain that displayed dates are in the device's timezone and are sent as UTC instants. Enter cargo weight in pounds. Show all three checkpoint spacing choices and select 25 miles.

## 1:40–2:45 — Routes

Calculate the trip. Explain loading and provider failure handling if relevant. Compare the actual returned alternatives, distance, duration, ETA, coverage, Severe miles, High miles, and average risk. If the provider returns fewer than three, show its warning rather than implying extra routes exist. Select another route and fit all alternatives on the map.

## 2:45–4:00 — Arrival weather and cargo

Click a checkpoint on the map or in the table. Show mile distance, coordinates, ETA, wind, rain, snowfall, forecast interval, and risk reason. Explain that rainfall includes liquid showers, snowfall uses snow depth in inches, and missing forecasts are Unknown. Explain the exact cargo thresholds and use the automated boundary tests for deterministic threshold examples; do not claim today's live weather happens to cross them.

## 4:00–5:00 — Recommendation

Show the recommended route and explain the strict comparison order: Severe miles, High miles, average risk, duration. Point out distance-weighted segments and the final partial interval. Explain that No Travel/incomplete-weather/non-truck sections exclude a route. If current live routes are all unsafe, show the actual no-safe-route state.

## 5:00–6:15 — Map and forecast slider

Toggle the weather layer. Move the slider through 0, 12, 24, and 48 hours, showing real selected timestamps. Inspect the same checkpoint's selected-hour and arrival-time weather. Explain that recommendations and road risk stay based on arrival, while the heatmap updates for a single corridor-wide hour. If real conditions are similar across hours, state that honestly. Explain that this is a spatial forecast sample layer rather than radar.

## 6:15–7:15 — Engineering and verification

Open the actual GitHub repository. Show the independent risk/checkpoint/recommendation modules, typed frontend contract, passing executed tests, and Docker/Render configuration. Explain server-side API keys, batching, cache lifetime, and the one-process deployment constraint. Mention uniform-speed ETA and sparse weather-sampling limitations.

## 7:15–8:00 — Submission links

Return to the working hosted app and confirm the final links: GitHub repository, hosted URL, and the recorded Loom. State any remaining limitation. Upload the real recording and update this file with its URL.

## Live acceptance checklist

- [ ] Real TomTom key authorized for both Search and Routing.
- [ ] Hosted `/api/health/` reports routing configured.
- [ ] Real origin/destination produces provider route geometry.
- [ ] All actual alternatives appear, with fewer-than-three handling when applicable.
- [ ] Checkpoints and final interval follow the road geometry.
- [ ] Arrival-time forecasts and risk reasons are visible.
- [ ] Slider changes the actual forecast response and heatmap, without reranking routes.
- [ ] Missing weather and No Travel do not produce a safe recommendation.
- [ ] Desktop and mobile views work at the hosted URL.
- [ ] GitHub repository and hosted links are accessible to the evaluator.
- [ ] Loom recording is 5–10 minutes and its URL works.
