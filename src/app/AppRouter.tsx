import { lazy, Suspense, useEffect } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import App from '../App'

const WorldPage = lazy(() => import('./WorldPage').then((m) => ({ default: m.WorldPage })))

/** Warm the world chunk after the landing is interactive (doesn’t compete with LCP). */
function usePrefetchWorld() {
  useEffect(() => {
    const run = () => {
      void import('./WorldPage')
    }
    if (typeof window.requestIdleCallback === 'function') {
      const id = window.requestIdleCallback(run, { timeout: 4000 })
      return () => window.cancelIdleCallback(id)
    }
    const t = globalThis.setTimeout(run, 2000)
    return () => globalThis.clearTimeout(t)
  }, [])
}

export function AppRouter() {
  usePrefetchWorld()
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />} />
        <Route
          path="/world/:paintingId"
          element={
            <Suspense
              fallback={
                <div className="world-shell world-shell--loading">
                  <p className="mono-label">Opening the frame…</p>
                </div>
              }
            >
              <WorldPage />
            </Suspense>
          }
        />
      </Routes>
    </BrowserRouter>
  )
}
