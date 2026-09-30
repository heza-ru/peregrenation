import { useEffect, useState } from 'react'

/** Prefer coarse pointer / no hover as "touch-first" (phones & tablets). */
export function useTouchPrimary(): boolean {
  const [touch, setTouch] = useState(() => {
    if (typeof window === 'undefined') return false
    return window.matchMedia('(hover: none), (pointer: coarse)').matches
  })

  useEffect(() => {
    const mq = window.matchMedia('(hover: none), (pointer: coarse)')
    const sync = () => setTouch(mq.matches)
    sync()
    mq.addEventListener('change', sync)
    return () => mq.removeEventListener('change', sync)
  }, [])

  return touch
}
