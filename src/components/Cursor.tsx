import { useEffect, useRef, useState } from 'react'
import { addFrame, FramePriority } from '../motion/frameLoop'
import { FINE_POINTER } from '../motion/interactions'

type CursorMode = 'idle' | 'link' | 'label' | 'hide'

function modeFor(target: Element | null): { mode: CursorMode; label: string } {
  const el = target?.closest('[data-cursor], a, button, label, [role="button"]')
  if (!el) return { mode: 'idle', label: '' }
  const value = el.getAttribute('data-cursor')
  if (value === 'hide') return { mode: 'hide', label: '' }
  if (value) return { mode: 'label', label: value }
  return { mode: 'link', label: '' }
}

/** Precise dot + a lagging ring that stretches with speed and morphs over interactive targets. */
export function Cursor({ reduced }: { reduced: boolean }) {
  const [fine, setFine] = useState(() => window.matchMedia(FINE_POINTER).matches)
  const enabled = fine && !reduced
  const rootRef = useRef<HTMLDivElement>(null)
  const ringRef = useRef<HTMLDivElement>(null)
  const dotRef = useRef<HTMLDivElement>(null)
  const labelRef = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    const mq = window.matchMedia(FINE_POINTER)
    const update = () => setFine(mq.matches)
    mq.addEventListener('change', update)
    return () => mq.removeEventListener('change', update)
  }, [])

  useEffect(() => {
    const root = rootRef.current
    const ring = ringRef.current
    const dot = dotRef.current
    const labelEl = labelRef.current
    if (!enabled || !root || !ring || !dot || !labelEl) return

    const html = document.documentElement
    html.classList.add('has-cursor')
    const s = { x: 0, y: 0, rx: 0, ry: 0, vx: 0, vy: 0, shown: false }
    let mode: CursorMode = 'idle'

    const setMode = (next: CursorMode, label: string) => {
      if (next === mode && labelEl.textContent === label) return
      root.classList.remove(`cursor--${mode}`)
      mode = next
      root.classList.add(`cursor--${mode}`)
      labelEl.textContent = label
    }
    setMode('idle', '')

    const onMove = (e: PointerEvent) => {
      if (e.pointerType !== 'mouse') return
      s.x = e.clientX
      s.y = e.clientY
      if (!s.shown) {
        s.rx = s.x
        s.ry = s.y
        s.shown = true
        root.classList.add('is-shown')
      }
      const next = modeFor(e.target instanceof Element ? e.target : null)
      setMode(next.mode, next.label)
    }
    const onOut = (e: PointerEvent) => {
      if (e.relatedTarget) return
      s.shown = false
      root.classList.remove('is-shown')
    }
    const onDown = () => root.classList.add('is-down')
    const onUp = () => root.classList.remove('is-down')

    const removeFrame = addFrame((_, dt) => {
      if (!s.shown) return
      const k = 1 - Math.exp(-dt * (mode === 'label' ? 10 : 16))
      const px = s.rx
      const py = s.ry
      s.rx += (s.x - s.rx) * k
      s.ry += (s.y - s.ry) * k
      const kv = 1 - Math.exp(-dt * 12)
      s.vx += ((s.rx - px) / Math.max(dt, 1 / 240) - s.vx) * kv
      s.vy += ((s.ry - py) / Math.max(dt, 1 / 240) - s.vy) * kv

      dot.style.transform = `translate3d(${s.x.toFixed(1)}px, ${s.y.toFixed(1)}px, 0)`
      const speed = Math.hypot(s.vx, s.vy)
      const stretch = mode === 'idle' ? Math.min(0.45, speed / 4000) : 0
      const angle = stretch > 0.002 ? Math.atan2(s.vy, s.vx) : 0
      ring.style.transform = `translate3d(${s.rx.toFixed(1)}px, ${s.ry.toFixed(1)}px, 0) rotate(${angle.toFixed(3)}rad) scale(${(1 + stretch).toFixed(3)}, ${(1 - stretch * 0.6).toFixed(3)})`
    }, FramePriority.render)

    window.addEventListener('pointermove', onMove, { passive: true })
    document.addEventListener('pointerout', onOut)
    window.addEventListener('pointerdown', onDown)
    window.addEventListener('pointerup', onUp)
    return () => {
      removeFrame()
      html.classList.remove('has-cursor')
      window.removeEventListener('pointermove', onMove)
      document.removeEventListener('pointerout', onOut)
      window.removeEventListener('pointerdown', onDown)
      window.removeEventListener('pointerup', onUp)
    }
  }, [enabled])

  if (!enabled) return null

  return (
    <div ref={rootRef} className="cursor" aria-hidden="true">
      <div ref={ringRef} className="cursor__ring">
        <div className="cursor__shape">
          <span ref={labelRef} className="cursor__label" />
        </div>
      </div>
      <div ref={dotRef} className="cursor__dot" />
    </div>
  )
}
