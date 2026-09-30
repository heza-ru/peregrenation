import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { AppRouter } from './app/AppRouter'
import { startPreloader } from './boot/preloader'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AppRouter />
  </StrictMode>,
)

startPreloader(
  new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))),
)
