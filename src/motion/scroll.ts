import type Lenis from 'lenis'

let lenis: Lenis | null = null

export function setLenis(instance: Lenis | null) {
  lenis = instance
}

const easeInOutQuart = (t: number) => (t < 0.5 ? 8 * t * t * t * t : 1 - Math.pow(-2 * t + 2, 4) / 2)

/** Glide to an element or offset; long jumps take longer so the painted transitions stay legible. */
export function scrollToTarget(target: HTMLElement | number) {
  const top = typeof target === 'number' ? target : target.getBoundingClientRect().top + window.scrollY
  if (!lenis) {
    window.scrollTo({ top, behavior: 'smooth' })
    return
  }
  // A menu may still hold the lock when its link fires; restarting later would cancel this glide
  if (lenis.isStopped) {
    lenis.start()
    document.documentElement.classList.remove('scroll-locked')
  }
  const distance = Math.abs(top - window.scrollY) / window.innerHeight
  lenis.scrollTo(top, {
    duration: Math.min(3.2, 1.1 + distance * 0.22),
    easing: easeInOutQuart,
  })
}

export function lockScroll(locked: boolean) {
  document.documentElement.classList.toggle('scroll-locked', locked)
  if (locked) lenis?.stop()
  else lenis?.start()
}

/** Signed scroll velocity in px per frame (0 without smooth scroll). */
export function scrollVelocity(): number {
  return lenis?.velocity ?? 0
}
