import { useEffect, useState } from 'react'

export type Theme = 'light' | 'dark'

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(() => {
    try { return localStorage.getItem('spotter-theme') === 'light' ? 'light' : 'dark' }
    catch { return 'dark' }
  })

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', theme === 'dark' ? '#1b2521' : '#edf2e9')
    try { localStorage.setItem('spotter-theme', theme) } catch { /* Preference is optional when browser storage is unavailable. */ }
  }, [theme])

  return { theme, setTheme }
}
