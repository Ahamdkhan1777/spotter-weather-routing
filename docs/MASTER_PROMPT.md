# MASTER IMPLEMENTATION PROMPT
## Spotter AI — Weather-Aware Truck Routing
### React + Django Full Stack Developer Assessment

You are acting as a **Senior Full-Stack Engineer, Technical Architect, Backend Engineer, Frontend Engineer, QA Engineer, and Deployment Engineer**.

Your task is to implement a complete, working, professional-quality application based on the attached Spotter AI Full Stack Developer assessment.

Do not merely explain how to build it. You must inspect the project, plan the implementation, write the code, integrate APIs, test the application, fix issues, and prepare the final submission.

The goal is to deliver a reliable, polished application that satisfies the assessment requirements within the stated maximum of **16 working hours and 4 days**.

---

# Assessment Strategy and Priorities

This assessment is focused on two major scoring areas:

- Routing correctness: 40%
- UI, map, and heatmap experience: 40%
- Code quality: 15%
- Documentation and walkthrough: 5%

Prioritize the routing pipeline and map experience above secondary features.

The core workflow is:

Trip Inputs → Route Alternatives → Distance Checkpoints → Arrival-Time Weather → Weather and Load Risk → Route Ranking → Map Visualization.

Build a complete, working end-to-end flow before adding optional functionality.

### Development priorities

1. Establish a clean, separate Git repository for this project. Do not accidentally use or modify a parent-directory Git repository.
2. Define API contracts, data models, risk rules, and calculation tests.
3. Implement route generation and alternative-route handling.
4. Implement distance-based checkpoints and estimated arrival times.
5. Integrate weather forecasts using checkpoint coordinates and estimated arrival times.
6. Implement and test weather/load risk classification.
7. Implement deterministic route ranking and No Travel exclusion.
8. Build the React map experience with route alternatives, checkpoints, risk indicators, and route summaries.
9. Implement the forecast heatmap and 0–48-hour slider.
10. Deploy, document, and prepare the walkthrough.

Do not build authentication, user accounts, saved trips, dashboards, fleet management, or unrelated features unless explicitly required.

### Technical correctness requirements

- Generate up to three distinct route alternatives. Never fabricate alternatives if the provider returns fewer.
- Generate checkpoints along actual road geometry using cumulative route distance.
- Include origin and destination checkpoints.
- Calculate checkpoint ETAs using travel time along the route.
- Fetch weather using both checkpoint coordinates and estimated arrival time.
- Classify wind, rain, and snow independently, then use the highest severity.
- Apply load-specific overrides after weather classification.
- Exclude routes containing No Travel conditions from recommended routes.
- If all routes contain No Travel conditions, clearly display that no safe route is available.
- Rank eligible routes lexicographically: Severe miles, High miles, average risk, then travel time.
- Calculate risk using distance-weighted road segments, not checkpoint counts.
- Never classify unavailable weather data as Low risk.
- Clearly distinguish arrival-time checkpoint forecasts from the heatmap's selected forecast hour.
- Ensure the forecast slider updates the actual heatmap data, not merely its label.

### Boundary and edge-case handling

Use a documented, deterministic boundary convention. Where threshold intervals overlap, assign the shared boundary to the higher severity.

Handle:

- Fewer than three available routes.
- Missing or invalid weather data.
- Forecast horizon limitations.
- Time-zone and daylight-saving conversions.
- Final partial checkpoint intervals.
- Provider timeouts and rate limits.
- Routes with No Travel segments.
- All routes being unsafe.
- Missing ETA or geometry data.

Do not hide limitations or invent missing data. Display clear warnings where appropriate.

# Usage and Implementation Efficiency

Work efficiently and avoid unnecessary reasoning or repeated repository analysis.

- Use the selected model and reasoning effort appropriate to the complexity of each task.
- Do not repeatedly inspect files that have not changed.
- Do not rewrite working components unnecessarily.
- Do not regenerate the entire project when a targeted modification is sufficient.
- Avoid excessive explanations and lengthy planning before implementation.
- Inspect relevant files, make the required changes, run focused tests, and report results.
- Reuse existing implementations, API clients, types, and utilities where appropriate.
- Prefer small, coherent changes that can be tested independently.
- Do not sacrifice correctness or testing to reduce usage.
- If blocked, explain the specific blocker and propose the smallest practical solution.

After completing each phase, provide a concise report:

1. What was implemented.
2. Which files changed.
3. Which tests were run and their results.
4. Any remaining issues.
5. The next implementation task.

Do not stop after producing a plan. Continue implementing the requested phase.

---

# 1. ORIGINAL ASSESSMENT — SOURCE OF TRUTH

Build a React + Django web application that helps truck drivers choose the safest route based on:

- Origin
- Destination
- Departure date and time
- Load weight

The application must:

1. Generate three route options using a routing API.
2. Sample weather every 10, 25, or 50 miles along each route.
3. Use the truck's estimated arrival time at each checkpoint to retrieve weather forecasts.
4. Calculate weather risk using the exact supplied weather and load rules.
5. Recommend the best route by following the specified priority order.
6. Display all routes, checkpoints, risk levels, ETAs, and route summaries on a map.
7. Display a weather heatmap along the trip corridor.
8. Include a forecast slider covering 0–48 hours.

Third-party routing, geocoding, and weather APIs are allowed.

You do not need to develop your own routing engine.

**The original assessment is the primary authority. Do not replace its requirements with your own interpretation.**

---

# 2. EVALUATION PRIORITIES

The application will be evaluated using:

| Evaluation area | Weight |
|---|---:|
| Routes, weather, risk and recommendation logic | 40% |
| UI, map, heatmap smoothness and performance | 40% |
| Code quality | 15% |
| Documentation and walkthrough | 5% |

Use these weights to prioritize implementation.

The first 80% of the evaluation concerns application functionality and user experience.

Therefore:

- Do not spend excessive time on unnecessary backend abstractions.
- Do not build features that are not required.
- Do not sacrifice calculation correctness for visual design.
- Do not deliver a beautiful interface with fake route or weather data.
- Do not deliver a technically correct backend with an incomplete or broken interface.

Prioritize a complete, reliable end-to-end application.

---

# 3. FIRST ACTION — INSPECT THE EXISTING PROJECT

Before writing code:

1. Inspect the current working directory.
2. Identify existing frontend and backend folders.
3. Identify the existing framework versions.
4. Inspect package.json and Python dependencies.
5. Check existing API integrations.
6. Check environment files and configuration.
7. Check whether a database is already configured.
8. Check existing components, routes, serializers, models, and services.
9. Check whether any code has already been written for the assessment.
10. Identify incomplete or broken functionality.

Do not overwrite existing work without understanding it.

If the project is empty, create a clean structure.

If the project is partially implemented, preserve useful working code and improve it.

Before implementation, provide a concise summary of:

- Existing project structure
- What is already working
- What is missing
- What needs to be changed
- Proposed implementation sequence

Then proceed with implementation.

Do not stop after producing the plan.

---

# 4. TECHNOLOGY STACK

Use the required technologies.

## Frontend

- React
- TypeScript
- Vite
- Tailwind CSS
- React Router if multiple pages are necessary
- MapLibre GL JS for map visualization
- Lucide icons or another consistent icon library

## Backend

- Python
- Django
- Django REST Framework

## Routing

Preferred candidate:

TomTom Routing API.

Verify the current API documentation before implementation.

Check:

- Route calculation
- Alternative routes
- Truck travel mode
- Vehicle restrictions
- Route distance
- Estimated travel time
- Departure-time support
- Route geometry
- API limits and authentication

The assessment requires three route options. Request a main route and alternatives where supported.

Important: A routing provider may return fewer than three routes. Never fabricate additional routes.

## Weather

Preferred candidate:

Open-Meteo Forecast API.

Verify current documentation and availability of:

- Hourly wind speed
- Hourly rain
- Hourly snowfall
- Forecast timestamps
- Time zones
- Forecast horizon
- Units

Use consistent units:

- Wind: mph
- Rain: inches per hour
- Snow: inches per hour
- Distance: miles
- Load: pounds

If an API returns different units, convert them correctly before applying risk rules.

## Geocoding

Use a reliable geocoding provider compatible with the routing provider.

Do not assume that the user will always enter coordinates.

The application must support human-readable origin and destination input.

## Hosting

Choose deployment services that support the actual application architecture.

Possible options:

- Frontend: Vercel
- Backend: Render or another Python-compatible hosting service

Verify current free-tier limitations, deployment requirements, and environment-variable support.

Do not promise that a service offers free hosting if its current terms do not support it.

---

# 5. APPLICATION ARCHITECTURE

Build a maintainable frontend/backend architecture.

Suggested structure:

    project/
    |
    |-- frontend/
    |   |-- src/
    |   |   |-- components/
    |   |   |-- pages/
    |   |   |-- hooks/
    |   |   |-- services/
    |   |   |-- types/
    |   |   |-- utils/
    |   |   |-- styles/
    |   |   |-- App.tsx
    |   |   |-- main.tsx
    |   |-- package.json
    |   |-- .env.example
    |
    |-- backend/
    |   |-- config/
    |   |-- routing/
    |   |   |-- views.py
    |   |   |-- serializers.py
    |   |   |-- urls.py
    |   |-- services/
    |   |   |-- geocoding.py
    |   |   |-- routing.py
    |   |   |-- weather.py
    |   |   |-- checkpoints.py
    |   |   |-- risk_engine.py
    |   |   |-- recommendation.py
    |   |-- tests/
    |   |-- manage.py
    |   |-- requirements.txt
    |   |-- .env.example
    |
    |-- README.md
    |-- .gitignore

You may adjust the structure if the existing project requires it.

Keep business logic separate from API views.

The risk engine must be independent and testable.

---

# 6. USER INPUT FORM

Build a clear and responsive input form.

Required inputs:

### Origin

- Human-readable location
- Geocoded coordinates internally

### Destination

- Human-readable location
- Geocoded coordinates internally

### Departure date and time

- Date picker
- Time picker
- Correct timezone handling

### Load weight

- Numeric input
- Unit clearly displayed as pounds
- Positive value required

### Checkpoint interval

Provide three choices:

- 10 miles
- 25 miles
- 50 miles

The default can be 25 miles.

Validate all inputs.

Do not submit incomplete or invalid data.

Show useful validation messages.

---

# 7. ROUTE GENERATION

Use the routing API to calculate route options.

Requirements:

- Generate up to three distinct route options.
- Retrieve actual route geometry.
- Retrieve distance.
- Retrieve estimated duration.
- Retrieve expected arrival time.
- Preserve the route's original geometry.

If fewer than three routes are returned:

- Display the routes actually returned.
- Explain that fewer alternatives were available.
- Do not invent routes.
- Do not duplicate a route and present it as a different alternative.

If no route is returned:

- Show an informative error.
- Allow the user to retry.
- Do not continue risk calculations with fabricated geometry.

Where available, use truck-specific routing parameters.

If the provider does not support the requested truck configuration or cannot guarantee a suitable truck route, disclose that limitation.

Do not claim that a route is legally suitable for every truck merely because a routing API returned it.

---

# 8. ROUTE DISTANCE SAMPLING

This is a critical technical requirement.

Sample weather along the actual route geometry.

The user can choose:

- 10-mile intervals
- 25-mile intervals
- 50-mile intervals

Do not simply divide the number of coordinates by the number of checkpoints.

The correct approach:

1. Decode the route geometry.
2. Calculate cumulative distance along the route.
3. Place checkpoints at the selected distance interval.
4. Interpolate checkpoint coordinates along the route.
5. Include the destination as the final checkpoint when necessary.
6. Preserve the distance of each checkpoint from the origin.

For example, for a route of 117 miles with a 25-mile interval:

- 0 miles: Origin
- 25 miles
- 50 miles
- 75 miles
- 100 miles
- 117 miles: Destination

Every checkpoint must contain:

- Latitude
- Longitude
- Distance from origin
- Estimated arrival time
- Weather information
- Risk classification

Do not confuse checkpoint count with hazardous distance.

---

# 9. ESTIMATED ARRIVAL TIME AT EACH CHECKPOINT

Weather must correspond to the time the truck is expected to reach each checkpoint.

Do not fetch weather using only the departure time.

For each checkpoint:

1. Determine its distance from the origin.
2. Determine the route's estimated duration.
3. Estimate the travel time to that checkpoint.
4. Calculate its expected arrival timestamp.
5. Request or select the weather forecast corresponding to that timestamp.

A reasonable initial implementation is to interpolate travel time using cumulative distance and the route's estimated total duration.

If the routing API provides more detailed travel-time or segment information, use it where practical.

Clearly document the chosen approximation.

Handle:

- Timezones
- Daylight-saving changes
- Departures crossing midnight
- Forecast timestamps
- Forecasts beyond the provider's available horizon

If the required forecast is unavailable, show:

"Weather forecast unavailable for this checkpoint/time."

Never silently classify missing weather as Low risk.

---

# 10. WEATHER RISK RULES — EXACT REQUIREMENTS

Implement the supplied risk thresholds.

## Wind

| Wind speed | Risk |
|---|---|
| Less than 25 mph | Low |
| 25–34 mph | Moderate |
| 35–44 mph | High |
| 45–54 mph | Severe |
| 55 mph or above | No Travel |

## Rain

| Rain intensity | Risk |
|---|---|
| Less than 0.10 in/hr | Low |
| 0.10–0.25 | Moderate |
| 0.25–0.50 | High |
| 0.50–1.00 | Severe |
| Greater than 1.00 | No Travel |

## Snow

| Snow intensity | Risk |
|---|---|
| Less than 0.5 in/hr | Low |
| 0.5–1.0 | Moderate |
| 1.0–2.0 | High |
| 2.0–3.0 | Severe |
| Greater than 3.0 | No Travel |

Use the assessment's supplied thresholds.

## IMPORTANT: BOUNDARY HANDLING

Some supplied ranges overlap at exact boundary values.

For example:

- Rain 0.25
- Rain 0.50
- Wind 35
- Snow 1.0

Do not silently implement ambiguous ranges.

Define deterministic boundary handling, document it in the README, and keep it consistent throughout the backend and frontend.

Use the more severe classification at ambiguous shared boundaries as a conservative implementation choice, unless the assessment's source instructions specify otherwise.

Do not change the numeric thresholds.

---

# 11. LOAD-DEPENDENT WIND RULES

Implement the following additional rules exactly.

### Rule 1

Wind speed greater than or equal to 55 mph:

No Travel for every load weight.

### Rule 2

Wind speed between 45 and 54 mph AND load weight greater than 30,000 lb:

No Travel.

### Rule 3

Wind speed between 35 and 44 mph AND load weight greater than 40,000 lb:

Severe.

Important:

- Exactly 30,000 lb does not satisfy the greater-than-30,000 condition.
- Exactly 40,000 lb does not satisfy the greater-than-40,000 condition.
- Load thresholds must be tested carefully.

The final checkpoint risk should reflect the most severe applicable weather/load classification.

Use this severity order:

Low < Moderate < High < Severe < No Travel.

Do not allow a lower-risk weather condition to override a more severe load-related rule.

---

# 12. RISK ENGINE

Create independent backend functions.

Suggested functions:

    classify_wind()
    classify_rain()
    classify_snow()
    apply_load_rules()
    calculate_checkpoint_risk()
    calculate_route_risk()

The risk engine must:

- Accept normalized weather values.
- Accept the truck's load weight.
- Apply the supplied rules.
- Return the final classification.
- Explain which condition produced that classification.

Example response:

    {
      "wind_mph": 48,
      "rain_in_per_hour": 0.05,
      "snow_in_per_hour": 0,
      "load_weight_lb": 35000,
      "base_wind_risk": "Severe",
      "load_adjustment": "No Travel",
      "final_risk": "No Travel",
      "risk_reason": "Wind between 45 and 54 mph with load above 30000 lb"
    }

This is an illustrative structure, not a requirement to use this exact JSON schema.

---

# 13. ROUTE RISK SUMMARY

Calculate the risk for each route.

Show:

- Total route distance
- Low-risk miles
- Moderate-risk miles
- High-risk miles
- Severe-risk miles
- No Travel miles
- Average risk
- Estimated travel time
- Estimated arrival time

IMPORTANT:

Do not simply count checkpoints and call them miles.

Use distance-weighted checkpoint intervals.

For example:

If a checkpoint represents a 25-mile segment, account for the distance represented by that checkpoint when calculating route risk.

Handle the final shorter interval correctly.

The risk summary should remain reasonably consistent when the user switches between 10, 25, and 50-mile sampling.

Because the sampling interval changes, disclose that these are sampled estimates, not continuous meteorological measurements of every road segment.

---

# 14. ROUTE RECOMMENDATION LOGIC

Follow the exact priority order from the assessment:

1. Fewest Severe miles
2. Fewest High miles
3. Lowest average risk
4. Shortest travel time

Implement this as lexicographic comparison.

Do not replace it with an arbitrary weighted score.

The comparison should prioritize each criterion in sequence.

## No Travel safety rule

A route containing No Travel intervals must not be recommended as a safe route.

If all available routes contain No Travel intervals:

Display:

"No safe route available."

You may show the least risky available options for informational purposes, but clearly mark them as unsafe and do not label one as the safe recommendation.

If a route has unavailable weather data, do not automatically treat that route as safe.

Explain its incomplete risk coverage.

---

# 15. WEATHER HEATMAP

Build a real interactive weather heatmap along the trip corridor.

Requirements:

- Display route corridors on the map.
- Show weather-risk conditions using understandable visual encoding.
- Display risk-colored route segments.
- Show checkpoint markers.
- Allow users to inspect individual checkpoints.
- Display weather information and estimated arrival times.
- Include a 0–48-hour forecast slider.

The heatmap must be based on actual forecast data.

Do not create a decorative gradient that merely looks like weather data.

The heatmap should be visually distinguishable from route lines and checkpoint markers.

Use a clear legend.

Suggested risk colors:

- Low: Green
- Moderate: Yellow
- High: Orange
- Severe: Red
- No Travel: Dark red

Keep the interface accessible and make sure colors are accompanied by labels or icons.

---

# 16. FORECAST SLIDER — 0 TO 48 HOURS

Implement a working forecast slider.

Range:

0–48 hours.

The slider must actually change the forecast visualization.

At the selected offset:

- Update the displayed weather data.
- Update the heatmap.
- Update checkpoint weather details.
- Show the selected forecast timestamp.
- Show the corresponding risk visualization.

IMPORTANT DISTINCTION:

The route recommendation must continue using the weather forecast at each checkpoint's estimated truck arrival time.

The slider is for exploring the forecast along the trip corridor.

Do not accidentally replace arrival-time-based route calculations with a single forecast timestamp.

If a forecast time is unavailable, communicate that clearly.

---

# 17. FRONTEND DESIGN

Build a polished, professional logistics dashboard.

The design should feel like a real transportation/logistics product.

Avoid:

- Generic starter-template appearance
- Excessive gradients
- Unnecessary animations
- Oversized empty cards
- Inconsistent spacing
- Decorative elements that reduce map visibility
- Unnecessary complexity

## Main dashboard layout

### Header

Include:

- Product name
- Small logo or icon
- Application status
- Responsive navigation if needed

Suggested name:

Weather-Aware Truck Routing

### Left control panel

Include:

- Origin
- Destination
- Departure date/time
- Load weight
- Checkpoint interval
- Calculate routes button

### Main map area

Include:

- Route geometry
- Three route options when available
- Risk-colored segments
- Checkpoint markers
- Weather heatmap
- Map controls
- Legend

### Route comparison section

Each route card should display:

- Route name
- Distance
- Travel time
- ETA
- Severe miles
- High-risk miles
- Average risk
- No Travel status
- Recommendation status

### Checkpoint details

When a user selects a checkpoint, show:

- Distance from origin
- Coordinates
- Estimated arrival time
- Wind speed
- Rain intensity
- Snow intensity
- Risk classification
- Risk explanation

### Forecast controls

Include:

- 0–48-hour slider
- Selected forecast offset
- Selected forecast timestamp
- Weather legend

---

# 18. RESPONSIVE DESIGN

Ensure the application works on:

- Desktop
- Laptop
- Tablet
- Mobile

On smaller screens:

- Stack the input form and route cards.
- Preserve map usability.
- Prevent horizontal overflow.
- Keep controls accessible.
- Ensure checkpoint details remain readable.

The desktop layout is the priority, but mobile must not be broken.

---

# 19. BACKEND API DESIGN

Create clear REST endpoints.

Suggested endpoints:

    POST /api/routes/calculate/
    GET  /api/routes/{id}/
    GET  /api/routes/{id}/checkpoints/
    GET  /api/routes/{id}/weather/
    GET  /api/health/

You may adjust these endpoints if a simpler architecture is more appropriate.

The route calculation endpoint should orchestrate:

1. Input validation
2. Geocoding
3. Route generation
4. Checkpoint generation
5. ETA calculation
6. Weather retrieval
7. Risk calculation
8. Route summary
9. Recommendation

Return structured JSON suitable for the frontend.

Use serializers for validation.

Use appropriate HTTP status codes.

Handle API failures and invalid requests gracefully.

---

# 20. EXTERNAL API INTEGRATION

Implement routing, geocoding, and weather as separate service modules.

Requirements:

- Store API keys in environment variables.
- Never expose private API keys in frontend code.
- Never commit secrets to GitHub.
- Add .env.example files.
- Add request timeouts.
- Handle rate limits.
- Handle invalid responses.
- Handle network failures.
- Avoid unnecessary duplicate requests.
- Cache appropriate responses when practical.

Use a configurable API provider so that the routing or weather service can be replaced without rewriting the risk engine.

Do not hardcode real user data or API responses.

Do not pretend an API request succeeded if it failed.

If a service is unavailable, return a clear error or an explicitly labelled unavailable status.

---

# 21. API LIMITS AND MISSING CREDENTIALS

The application must remain understandable when API credentials are missing.

If credentials are unavailable:

1. Complete the integration code.
2. Add clear environment-variable instructions.
3. Provide .env.example.
4. Implement a clearly labelled development/demo mode only if needed.
5. Do not mix mock data with real API data without disclosure.
6. Do not claim that real routing or weather functionality has been verified if the API keys were never configured.

Use realistic test fixtures for automated tests.

The final README must clearly explain which credentials are required and how to obtain them.

---

# 22. ERROR HANDLING AND EDGE CASES

Handle the following cases:

### User input

- Empty origin
- Empty destination
- Same origin and destination
- Invalid location
- Invalid load weight
- Negative load weight
- Missing departure date
- Invalid date/time

### Routing

- No route found
- Only one route returned
- Only two routes returned
- Duplicate route alternatives
- Invalid route geometry
- API timeout
- API rate limit
- Truck mode unavailable

### Weather

- Weather API unavailable
- Missing wind data
- Missing rain data
- Missing snow data
- Forecast outside supported horizon
- Missing checkpoint forecast
- Invalid units
- Timezone mismatch

### Risk

- Exact threshold values
- Exact load boundaries
- Missing weather values
- No Travel conditions
- Routes with incomplete weather coverage

### Frontend

- Loading states
- Empty states
- API errors
- Retry actions
- No recommendation available
- Map rendering failure
- Slider changes during loading

Never silently convert missing data into safe weather.

---

# 23. PERFORMANCE

Prioritize responsive interaction.

Implement:

- Efficient checkpoint generation
- Avoid unnecessary API calls
- Parallel weather retrieval where provider limits permit
- Request batching where supported
- Sensible caching
- Debounced location search
- Map layer updates without unnecessary full re-renders
- Loading indicators
- Clear progress feedback

Do not make the map freeze when multiple checkpoints are displayed.

Do not add complicated infrastructure that is unnecessary for this assessment.

---

# 24. SECURITY AND CODE QUALITY

Follow practical development standards.

Backend:

- Validate all incoming data.
- Keep secrets in environment variables.
- Configure CORS appropriately.
- Avoid exposing API keys.
- Handle exceptions properly.
- Keep business logic in service modules.
- Avoid excessive code duplication.

Frontend:

- Use TypeScript types.
- Keep components reasonably small.
- Separate API calls from UI components.
- Handle loading and error states.
- Avoid unnecessary dependencies.
- Keep state management simple.

General:

- Use meaningful names.
- Remove dead code.
- Avoid hardcoded API responses.
- Avoid unnecessary abstractions.
- Keep the application maintainable.

---

# 25. TESTING REQUIREMENTS

Write automated tests for the risk engine and route recommendation logic.

At minimum, test these cases:

## Wind boundaries

- 24.99 mph → Low
- 25 mph → Moderate
- 34 mph → Moderate
- 35 mph → High
- 44 mph → High
- 45 mph → Severe
- 54 mph → Severe
- 55 mph → No Travel

## Load rules

- Wind 50 mph, load 30,000 lb → Severe
- Wind 50 mph, load 30,001 lb → No Travel
- Wind 40 mph, load 40,000 lb → High
- Wind 40 mph, load 40,001 lb → Severe
- Wind 55 mph, any load → No Travel

## Rain boundaries

Test:

- 0.09
- 0.10
- 0.25
- 0.50
- 1.00
- 1.01

Verify the documented boundary convention.

## Snow boundaries

Test:

- 0.49
- 0.50
- 1.00
- 2.00
- 3.00
- 3.01

Verify the documented boundary convention.

## Route recommendation

Test:

- Route with fewer Severe miles wins.
- If Severe miles are equal, fewer High miles wins.
- If both are equal, lower average risk wins.
- If those are equal, shorter travel time wins.
- Route with No Travel conditions is not recommended as safe.
- All routes unsafe → "No safe route available."
- Incomplete weather data → route risk marked incomplete.

## Checkpoint tests

Test:

- 10-mile intervals
- 25-mile intervals
- 50-mile intervals
- Final partial interval
- Destination checkpoint
- ETA calculation
- Cumulative distance

## API tests

Test:

- Successful response
- Invalid input
- Missing API key
- API timeout
- API error
- No route returned
- Fewer than three alternatives

Do not claim tests passed unless you actually execute them.

---

# 26. IMPLEMENTATION ORDER

Work in this sequence.

### Phase 1 — Project setup

- Inspect existing files.
- Configure React and Django.
- Configure environment variables.
- Verify frontend/backend communication.

### Phase 2 — Core backend

- Implement input serializers.
- Implement geocoding.
- Implement routing.
- Implement checkpoint generation.
- Implement ETA calculations.
- Implement weather retrieval.

### Phase 3 — Risk engine

- Implement all weather thresholds.
- Implement load-dependent rules.
- Implement checkpoint risk.
- Implement distance-weighted route risk.
- Implement route ranking.
- Write unit tests.

### Phase 4 — Frontend

- Build the dashboard.
- Build the input form.
- Display routes.
- Display route summaries.
- Display checkpoints.
- Connect the frontend to real backend endpoints.

### Phase 5 — Map and heatmap

- Render route geometry.
- Render alternatives.
- Add risk-colored segments.
- Add checkpoint markers.
- Add checkpoint inspection.
- Implement the forecast slider.

### Phase 6 — Integration

- Test full origin-to-destination flow.
- Test multiple route alternatives.
- Verify weather timestamps.
- Verify risk calculations.
- Verify recommendation output.

### Phase 7 — Final polish

- Fix visual inconsistencies.
- Fix errors.
- Test responsiveness.
- Improve loading and error states.
- Verify README instructions.

### Phase 8 — Deployment

- Deploy frontend.
- Deploy backend.
- Configure environment variables.
- Verify production API communication.
- Test the deployed application.

### Phase 9 — Submission

- Finalize GitHub repository.
- Finalize README.
- Record Loom walkthrough.
- Verify all links.

---

# 27. STRICT 16-WORKING-HOUR TIME LIMIT

The assessment states no more than:

- 4 days
- 16 working hours

Respect this limit.

Suggested time allocation:

| Phase | Hours |
|---|---:|
| Project inspection and setup | 1 |
| Routing, geocoding and alternatives | 2 |
| Checkpoints, ETAs and weather | 2.5 |
| Risk engine and tests | 2 |
| Map, route cards and checkpoint UI | 3 |
| Heatmap and forecast slider | 2 |
| Deployment, README and Loom | 1.5 |
| Integration testing and contingency | 2 |
| **Total** | **16** |

This is a planning budget, not permission to exceed the assessment's limit.

If time becomes constrained:

1. Complete the core route calculation.
2. Complete correct weather sampling and ETA logic.
3. Complete risk rules and route recommendation.
4. Complete the interactive map and route comparison.
5. Complete the functional forecast slider.
6. Complete deployment and submission.

Do not spend time building unrelated features.

---

# 28. FEATURES NOT TO BUILD

Unless essential to the assessment, do not build:

- User registration
- Authentication
- Payment systems
- Admin dashboards
- Driver profiles
- Fleet management
- Historical analytics
- Database-heavy tracking systems
- Real-time GPS tracking
- A custom routing engine
- Unrequested AI chatbot
- Unrequested route optimization algorithms

Keep the scope controlled.

---

# 29. GIT AND GITHUB REQUIREMENTS

Create a clean GitHub repository.

Requirements:

- Meaningful folder structure
- Clear README
- .gitignore
- .env.example
- No committed secrets
- No unnecessary generated files
- Meaningful commit messages
- Working setup instructions

Use a clean commit history.

Do not make one giant commit if the implementation can reasonably be divided into meaningful stages.

Before submission:

- Check Git status.
- Check tracked files.
- Check for secrets.
- Check README accuracy.
- Verify repository accessibility.

---

# 30. README REQUIREMENTS

Write a professional README containing:

1. Project title
2. Project overview
3. Main features
4. Technology stack
5. Architecture overview
6. Prerequisites
7. Installation instructions
8. Backend setup
9. Frontend setup
10. Environment variables
11. API key configuration
12. How to run locally
13. API endpoints
14. Risk calculation rules
15. Boundary-handling assumptions
16. Route recommendation logic
17. Checkpoint and ETA calculation explanation
18. Forecast slider explanation
19. Testing instructions
20. Deployment links
21. Known limitations

Do not claim functionality that is not implemented.

---

# 31. LOOM VIDEO — 5 TO 10 MINUTES

Prepare a clear walkthrough of the actual working application.

Suggested structure:

### 0:00–0:45 — Introduction

- Introduce the project.
- Explain its purpose.
- Show the deployed application.

### 0:45–2:00 — User input

- Enter origin.
- Enter destination.
- Select departure date/time.
- Enter load weight.
- Select checkpoint interval.

### 2:00–3:30 — Route generation

- Show available routes.
- Compare distance and travel times.
- Explain route alternatives.

### 3:30–5:00 — Weather and risk

- Show checkpoints.
- Explain estimated arrival times.
- Show weather data.
- Explain load-dependent risk.

### 5:00–6:30 — Recommendation

- Compare route risk.
- Demonstrate the recommendation logic.
- Explain No Travel handling.

### 6:30–8:00 — Map and heatmap

- Show route colors.
- Inspect a checkpoint.
- Move the 0–48-hour slider.
- Explain how the forecast changes.

### 8:00–9:00 — Technical overview

- Show GitHub.
- Explain React/Django architecture.
- Mention testing and deployment.

### 9:00–10:00 — Closing

- Summarize the implementation.
- Show the deployed application working.

Record the real application.

Do not fabricate functionality or use screenshots as a substitute for a working demonstration.

---

# 32. FINAL QUALITY ASSURANCE CHECKLIST

Before calling the task complete, verify:

## Core functionality

- [ ] Origin input works.
- [ ] Destination input works.
- [ ] Departure date/time works.
- [ ] Load weight input works.
- [ ] Checkpoint interval selection works.
- [ ] Routing API integration works.
- [ ] Up to three routes are displayed.
- [ ] Fewer available routes are handled honestly.
- [ ] Route geometry is correct.

## Weather and risk

- [ ] Checkpoints follow actual route distance.
- [ ] Weather uses checkpoint arrival time.
- [ ] Wind rules are correct.
- [ ] Rain rules are correct.
- [ ] Snow rules are correct.
- [ ] Load rules are correct.
- [ ] Boundary conditions are tested.
- [ ] Distance-weighted risk summaries are correct.
- [ ] No Travel is handled safely.
- [ ] Missing weather is never treated as Low risk.

## UI

- [ ] All routes appear on the map.
- [ ] Checkpoints are visible.
- [ ] Risk colors are clear.
- [ ] Checkpoint details work.
- [ ] Route summaries work.
- [ ] Recommendation is visible.
- [ ] Heatmap is based on actual forecast data.
- [ ] Forecast slider works from 0 to 48 hours.
- [ ] Desktop layout works.
- [ ] Mobile layout is usable.

## Engineering

- [ ] Backend endpoints work.
- [ ] Frontend/backend integration works.
- [ ] API errors are handled.
- [ ] API keys are secure.
- [ ] Automated tests run successfully.
- [ ] No major console errors.
- [ ] No major backend errors.
- [ ] No unnecessary mock data in production.

## Submission

- [ ] GitHub repository is accessible.
- [ ] README is complete.
- [ ] .env.example exists.
- [ ] No secrets are committed.
- [ ] Hosted frontend works.
- [ ] Hosted backend works.
- [ ] Production API integration works.
- [ ] Loom video is recorded.
- [ ] GitHub, hosted app and Loom links are ready.

---

# 33. FINAL EXECUTION RULES

These instructions are mandatory.

1. Do not stop at planning.
2. Do not merely provide example code.
3. Actually inspect and implement the project.
4. Do not skip essential requirements.
5. Do not invent API responses.
6. Do not use fake routes in production.
7. Do not silently ignore missing weather data.
8. Do not change the supplied risk thresholds.
9. Do not replace the specified route-ranking order.
10. Do not claim deployment success without verification.
11. Do not claim tests passed without running them.
12. Do not expose API secrets.
13. Do not build unnecessary features.
14. Do not exceed the 16-working-hour assessment scope.
15. Explain any requirement that cannot be implemented because of an API limitation or missing credential.
16. If a decision is ambiguous, make a conservative, documented assumption and continue rather than silently changing the requirements.
17. Ask me a question only when an essential decision genuinely cannot be made safely from the assessment or project context.
18. Preserve working code and avoid unnecessary rewrites.
19. Prefer a complete, reliable implementation over an ambitious incomplete one.
20. Keep the original assessment as the source of truth.

---

# 34. FINAL RESPONSE AFTER IMPLEMENTATION

When implementation is complete, provide:

## A. Implementation summary

- What was built
- Main features implemented
- Architecture
- External APIs used

## B. Testing summary

- Tests executed
- Tests passed
- Tests failed
- Any untested functionality

## C. Deployment

- Frontend URL
- Backend URL
- Deployment status

## D. GitHub

- Repository URL
- Important project structure
- Commit status

## E. Loom

- Walkthrough recording status
- Loom URL, once actually created

## F. Remaining issues

Clearly list:

- Missing API keys
- Provider limitations
- Incomplete features
- Forecast limitations
- Deployment problems
- Anything requiring manual action

Do not hide incomplete work.

## G. Assessment readiness

Give an honest final assessment of whether the application satisfies each original requirement.

Use:

- Complete
- Partially complete
- Not implemented
- Blocked by external dependency

Do not give a fabricated score or guarantee that I will pass.

---

# START NOW

First inspect the existing project and the attached assessment.

Then provide a concise implementation plan and immediately begin building.

**Your objective is to deliver a complete, functional, professionally presented, tested, and deployed Weather-Aware Truck Routing application that satisfies the original Spotter AI assessment within its 16-working-hour limit.**
