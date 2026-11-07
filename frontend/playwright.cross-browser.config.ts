import { defineConfig, devices } from '@playwright/test'
import base from './playwright.config'

export default defineConfig(base, {
  // Keep the normal Chromium suite unchanged; this command is a focused local smoke check.
  grep: /sanitizes adjacent|calculates a trip, inspects|risk rules support|checkpoint details leave|mobile calculated trip|both themes remain/,
  timeout: 60000,
  projects: [
    { name: 'firefox', use: { ...devices['Desktop Firefox'], viewport: { width: 1440, height: 1080 } } },
    { name: 'webkit', use: { ...devices['Desktop Safari'], viewport: { width: 1440, height: 1080 } } },
  ],
})
