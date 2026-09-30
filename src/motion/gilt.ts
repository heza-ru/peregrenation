import { useEffect } from 'react'
import { addFrame, FramePriority } from './frameLoop'

/** Without a mouse for this long the lamp drifts across the gilding on its own */
const MOUSE_IDLE = 4000

/**
 * Chapter titles are gilded: a burnished gold layer on every letter is only visible where
 * the lamp (the cursor, lagging slightly) falls on it, like gold leaf catching candlelight.
 */
export function useGilt(reduced: boolean) {
  useEffect(() => {
    if (reduced) return
    const titles = Array.from(document.querySelectorAll<HTMLElement>('.chapter__title'))
    if (!titles.length) return

    const place = () => {
      for (const title of titles) {
        for (const span of title.querySelectorAll<HTMLElement>('span')) {
          span.style.setProperty('--ox', `${span.offsetLeft}px`)
          span.style.setProperty('--oy', `${span.offsetTop}px`)
        }
      }
    }
    place()
    void document.fonts.ready.then(place)
    const ro = new ResizeObserver(place)
    titles.forEach((t) => ro.observe(t))

    const ptr = { x: 0, y: 0, seen: -Infinity }
    const onMove = (e: PointerEvent) => {
      if (e.pointerType !== 'mouse') return
      ptr.x = e.clientX
      ptr.y = e.clientY
      ptr.seen = performance.now()
    }
    window.addEventListener('pointermove', onMove, { passive: true })

    const lamps = titles.map(() => ({ x: 0, y: 0, placed: false }))
    const remove = addFrame((now, dt) => {
      const vh = window.innerHeight
      const mouse = now - ptr.seen < MOUSE_IDLE
      const s = now / 1000
      titles.forEach((title, i) => {
        const r = title.getBoundingClientRect()
        if (r.bottom < 0 || r.top > vh) return
        const tx = mouse ? ptr.x - r.left : r.width * (0.5 + 0.62 * Math.sin(s * 0.35 + i))
        const ty = mouse ? ptr.y - r.top : r.height * (0.4 + 0.25 * Math.cos(s * 0.5 + i))
        const lamp = lamps[i]
        const k = lamp.placed ? 1 - Math.exp(-dt * (mouse ? 9 : 2)) : 1
        lamp.x += (tx - lamp.x) * k
        lamp.y += (ty - lamp.y) * k
        lamp.placed = true
        title.style.setProperty('--gx', `${lamp.x.toFixed(1)}px`)
        title.style.setProperty('--gy', `${lamp.y.toFixed(1)}px`)
      })
    }, FramePriority.state)

    return () => {
      remove()
      ro.disconnect()
      window.removeEventListener('pointermove', onMove)
    }
  }, [reduced])
}
