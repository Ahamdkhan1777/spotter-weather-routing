import { expect, test, type Page } from '@playwright/test'

// Isolated browser fixtures only: no fixture imports in application source or production bundle.
function fixture() {
  const departure = new Date(Date.now()+3600000).toISOString()
  const risk = { level: 'Low', complete: true, reason: 'Wind, rain, and snow below assessment thresholds.', conditions: { wind: 'Low', rain: 'Low', snow: 'Low' } }
  const weather = { forecast_at: Math.ceil(Date.now()/3600000)*3600, wind_mph: 12, rain_in_per_hour: 0, snow_in_per_hour: 0 }
  const checkpoints = [[-96.8, 32.8], [-96.5, 32.5], [-96.2, 32.2]].map((coordinates, i) => ({ id: `route-1-cp-${i}`, coordinates, distance_miles: i*25, eta: new Date(new Date(departure).getTime()+i*1800000).toISOString(), risk, weather }))
  const route = { id: 'route-1', name: 'Route 1', geometry: { type: 'LineString', coordinates: checkpoints.map(p => p.coordinates) }, distance_miles: 50, duration_seconds: 3600, arrival_at: checkpoints[2].eta, truck_supported: true, checkpoints,
    segments: checkpoints.slice(1).map((point, i) => ({ start_miles: i*25, end_miles: (i+1)*25, risk: 'Low', geometry: { type: 'LineString', coordinates: [checkpoints[i].coordinates, point.coordinates] } })),
    summary: { risk_miles: { Low: 50, Moderate: 0, High: 0, Severe: 0, 'No Travel': 0, Unknown: 0 }, average_risk: 0, coverage_percent: 100, complete: true, blocked: false, eligible: true } }
  return { id: 'test-trip', origin: { label: 'Dallas, TX', coordinates: [-96.8, 32.8] }, destination: { label: 'Austin, TX', coordinates: [-96.2, 32.2] }, departure_at: departure, forecast_base_at: departure, load_weight_lb: 35000, interval_miles: 25,
    routes: [route], recommended_route_id: 'route-1', recommendation_reason: 'Fewest Severe miles, then High miles, average risk, then travel time.', warnings: ['The provider returned 1 distinct route option; no routes were invented.'], providers: { routing: 'test fixture', weather: 'test fixture' } }
}

async function mockAPI(page: Page, configured = true) {
  const trip = fixture()
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url())
    if (url.pathname.endsWith('/health/')) return route.fulfill({ json: { status: 'ok', routing_configured: configured, demo_mode: false } })
    if (url.pathname.endsWith('/calculate/')) return route.fulfill({ json: trip })
    if (url.pathname.endsWith('/forecast/')) {
      const hour = Number(url.searchParams.get('hour'))
      const checkpoints = trip.routes[0].checkpoints.map(p => ({ id: p.id, coordinates: p.coordinates, kind: 'checkpoint', weather: { ...p.weather, wind_mph: hour === 48 ? 60 : 12 }, risk: { ...p.risk, level: hour === 48 ? 'No Travel' : 'Low' } }))
      const corridor = checkpoints.flatMap((p, index) => [-0.12, 0, 0.12].map(offset => ({ ...p, id: `corridor-${index}-${offset}`, kind: 'corridor', coordinates: [p.coordinates[0]+offset, p.coordinates[1]] })))
      const points = [...checkpoints, ...corridor]
      return route.fulfill({ json: { hour, timestamp: new Date(new Date(trip.departure_at).getTime()+hour*3600000).toISOString(), points, missing_count: 0, total_points: points.length } })
    }
    return route.fulfill({ json: { places: [] } })
  })
}

test('calculates a trip, inspects checkpoints, and keeps recommendation independent of the slider', async ({ page }) => {
  await mockAPI(page)
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  await page.goto('/')
  await page.getByRole('button', { name: /Find the safest route/ }).click()
  await expect(page.getByText('Route 1 is recommended')).toBeVisible()
  await expect(page.getByText('1 available', { exact: true })).toBeVisible()
  await expect(page.locator('.map-wrapper')).toHaveAttribute('data-map-status', 'ready', { timeout: 30000 })
  const mapCanvas = await page.locator('canvas.maplibregl-canvas').boundingBox()
  expect(mapCanvas!.height).toBeGreaterThan(350)
  expect(mapCanvas!.width).toBeGreaterThan(500)
  await page.getByRole('button', { name: 'Checkpoint 1', exact: true }).click()
  await expect(page.getByRole('complementary', { name: 'Checkpoint details' })).toBeVisible()
  await page.getByRole('slider', { name: 'Forecast hour offset' }).fill('48')
  await expect(page.getByText('Corridor forecast · +48h')).toBeVisible()
  await expect(page.getByRole('complementary', { name: 'Checkpoint details' }).getByText('No Travel', { exact: true })).toBeVisible()
  await expect(page.getByText('Route 1 is recommended')).toBeVisible()
  await expect(page.getByRole('row').filter({ hasText: 'Checkpoint 1' }).getByText('Low', { exact: true })).toBeVisible()
  await page.screenshot({ path: 'test-results/desktop-trip.png', fullPage: true })
  expect(errors).toEqual([])
})

test('displays setup limitations and has no horizontal overflow on mobile', async ({ page }) => {
  await mockAPI(page, false)
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await expect(page.getByText('Connect your routing provider to get started')).toBeVisible()
  await expect(page.getByRole('slider')).toBeDisabled()
  await expect(page.getByText('Good decisions start with a little perspective.')).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: 'test-results/mobile-setup.png', fullPage: true })
})

test('clears stale setup status automatically without reloading or losing trip inputs', async ({ page }) => {
  await mockAPI(page, false)
  let configured = false
  await page.route('**/api/health/', route => route.fulfill({ json: { status: 'ok', routing_configured: configured, demo_mode: false } }))
  await page.goto('/')
  await expect(page.getByText('Connect your routing provider to get started')).toBeVisible()
  await page.getByLabel('Origin', { exact: true }).fill('Houston, TX')
  configured = true
  await expect(page.getByText('Routing service ready', { exact: true })).toBeVisible({ timeout: 10000 })
  await expect(page.getByText('Connect your routing provider to get started')).toHaveCount(0)
  await expect(page.getByLabel('Origin', { exact: true })).toHaveValue('Houston, TX')
})

test('allows an immediate configuration recheck from the setup banner', async ({ page }) => {
  await mockAPI(page, false)
  let configured = false
  await page.route('**/api/health/', route => route.fulfill({ json: { status: 'ok', routing_configured: configured, demo_mode: false } }))
  await page.goto('/')
  await expect(page.getByText('Connect your routing provider to get started')).toBeVisible()
  configured = true
  await page.getByRole('button', { name: 'Check again', exact: true }).click()
  await expect(page.getByText('Routing service ready', { exact: true })).toBeVisible()
  await expect(page.getByText('Connect your routing provider to get started')).toHaveCount(0)
})

test('shows API errors and allows a corrected retry', async ({ page }) => {
  await mockAPI(page)
  await page.route('**/api/routes/calculate/', route => route.fulfill({ status: 504, json: { error: { message: 'TomTom routing timed out. Please retry.' } } }))
  await page.goto('/')
  await page.getByRole('button', { name: /Find the safest route/ }).click()
  await expect(page.getByRole('alert').filter({ hasText: 'TomTom routing timed out' })).toBeVisible()
  await expect(page.getByRole('button', { name: /Find the safest route/ })).toBeEnabled()
  await page.unroute('**/api/routes/calculate/')
  await page.getByRole('button', { name: /Find the safest route/ }).click()
  await expect(page.getByText('Route 1 is recommended')).toBeVisible()
})

test('mobile calculated trip remains usable and exposes all checkpoint details', async ({ page }) => {
  await mockAPI(page)
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await page.getByRole('button', { name: /Find the safest route/ }).click()
  await expect(page.getByText('Route 1 is recommended')).toBeVisible()
  await page.getByRole('button', { name: 'Destination', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Mile 50' })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: 'test-results/mobile-trip.png', fullPage: true })
})

test('shows all actual route alternatives and supports selection', async ({ page }) => {
  await mockAPI(page)
  const trip = fixture()
  const first = trip.routes[0]
  trip.routes = [first, ...[2, 3].map(index => ({ ...first, id: `route-${index}`, name: `Route ${index}`, duration_seconds: 3600+index*600,
    geometry: { ...first.geometry, coordinates: first.geometry.coordinates.map(([lon, lat], i) => [lon+(i === 1 ? index*0.1 : 0), lat]) },
    checkpoints: first.checkpoints.map(point => ({ ...point, id: point.id.replace('route-1', `route-${index}`) })) }))]
  await page.route('**/api/routes/calculate/', route => route.fulfill({ json: trip }))
  await page.goto('/')
  await page.getByRole('button', { name: /Find the safest route/ }).click()
  await expect(page.getByText('3 available', { exact: true })).toBeVisible()
  await expect(page.locator('.route-card')).toHaveCount(3)
  await page.locator('.route-card').filter({ hasText: 'Route 2' }).click()
  await expect(page.getByRole('heading', { name: 'Route 2 checkpoints' })).toBeVisible()
  await expect(page.locator('.route-card.selected')).toContainText('Route 2')
})

test('never presents an all-unsafe trip as recommended', async ({ page }) => {
  await mockAPI(page)
  const trip = fixture()
  const unsafe = { ...trip, recommended_route_id: null, recommendation_reason: 'No safe route available. All routes contain No Travel conditions.', routes: trip.routes.map(route => ({ ...route, summary: { ...route.summary, blocked: true, eligible: false, risk_miles: { ...route.summary.risk_miles, Low: 0, 'No Travel': 50 } } })) }
  await page.route('**/api/routes/calculate/', route => route.fulfill({ json: unsafe }))
  await page.goto('/')
  await page.getByRole('button', { name: /Find the safest route/ }).click()
  await expect(page.getByText('No safe route available.', { exact: true })).toBeVisible()
  await expect(page.locator('.route-card')).toContainText('No Travel')
  await expect(page.locator('.route-card.recommended')).toHaveCount(0)
})
