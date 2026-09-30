import { useEffect } from 'react'
import Lenis from 'lenis'
import { addFrame, FramePriority } from '../motion/frameLoop'
import { setLenis } from '../motion/scroll'

/** Shopify Editions-style inertia scroll (Lenis). Disabled when reduced motion is on. */
export function useLenis(reduced: boolean) {
  useEffect(() => {
    if (reduced) return

    const lenis = new Lenis({
      duration: 1.2,
      easing: (t: number) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      smoothWheel: true,
      touchMultiplier: 1.15,
      wheelMultiplier: 0.92,
      autoRaf: false,
    })
    setLenis(lenis)

    const remove = addFrame((time) => lenis.raf(time), FramePriority.scroll)

    return () => {
      remove()
      setLenis(null)
      lenis.destroy()
    }
  }, [reduced])
}
