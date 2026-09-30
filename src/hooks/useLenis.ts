import { useEffect } from 'react'
import Lenis from 'lenis'
import { addFrame, FramePriority } from '../motion/frameLoop'
import { isLiteUi, LITE_UI } from '../motion/interactions'
import { setLenis } from '../motion/scroll'

/**
 * Shopify Editions-style inertia scroll (Lenis).
 * Off for reduced motion and for touch / narrow screens, where it fights the native scroller.
 */
export function useLenis(reduced: boolean) {
  useEffect(() => {
    if (reduced) return

    const mq = window.matchMedia(LITE_UI)
    let lenis: Lenis | null = null
    let removeFrame = () => {}

    const stop = () => {
      removeFrame()
      removeFrame = () => {}
      lenis?.destroy()
      lenis = null
      setLenis(null)
    }

    const start = () => {
      stop()
      if (mq.matches || isLiteUi()) return
      lenis = new Lenis({
        duration: 1.2,
        easing: (t: number) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
        smoothWheel: true,
        touchMultiplier: 1.15,
        wheelMultiplier: 0.92,
        autoRaf: false,
      })
      setLenis(lenis)
      // The doorway preloader may already hold the lock before Lenis exists.
      if (document.documentElement.classList.contains('scroll-locked')) lenis.stop()
      removeFrame = addFrame((time) => lenis?.raf(time), FramePriority.scroll)
    }

    start()
    mq.addEventListener('change', start)
    return () => {
      mq.removeEventListener('change', start)
      stop()
    }
  }, [reduced])
}
