import { useEffect, useState } from 'react'
import { scrollToTarget } from '../motion/scroll'

export function usePrefersReducedMotion() {
  const [reduced, setReduced] = useState(false)

  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    const update = () => setReduced(mq.matches)
    update()
    mq.addEventListener('change', update)
    return () => mq.removeEventListener('change', update)
  }, [])

  return reduced
}

/** Staggered intersection reveals for .reveal / [data-reveal] */
export function useRevealSystem() {
  useEffect(() => {
    const nodes = document.querySelectorAll<HTMLElement>('.reveal, [data-reveal]')
    if (!('IntersectionObserver' in window)) {
      nodes.forEach((n) => n.classList.add('is-visible'))
      return
    }

    // Threshold 0: pinned runways (gallery) can be many viewports tall, so a ratio may never be reached
    const io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue
          const el = entry.target as HTMLElement
          el.classList.add('is-visible')
          const kids = el.querySelectorAll<HTMLElement>('[data-reveal-child]')
          kids.forEach((child, i) => {
            if (!child.style.getPropertyValue('--reveal-delay')) {
              child.style.setProperty('--reveal-delay', `${i * 90}ms`)
            }
            child.classList.add('is-visible')
          })
          io.unobserve(el)
        }
      },
      { threshold: 0, rootMargin: '0px 0px -18% 0px' },
    )

    nodes.forEach((n) => io.observe(n))
    return () => io.disconnect()
  }, [])
}

/** Route in-page anchors through the smooth-scroll engine */
export function useSmoothAnchors(reduced: boolean) {
  useEffect(() => {
    if (reduced) return
    const onClick = (e: MouseEvent) => {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey) return
      const a = (e.target as HTMLElement | null)?.closest?.('a[href^="#"]') as HTMLAnchorElement | null
      const id = a?.getAttribute('href')?.slice(1)
      if (!id) return
      const el = document.getElementById(id)
      if (!el) return
      e.preventDefault()
      scrollToTarget(id === 'top' ? 0 : el)
      history.replaceState(null, '', `#${id}`)
    }
    document.addEventListener('click', onClick)
    return () => document.removeEventListener('click', onClick)
  }, [reduced])
}
