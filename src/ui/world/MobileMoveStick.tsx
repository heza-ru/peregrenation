import { useCallback, useEffect, useRef } from 'react'
import { useWorldStore } from '../../app/worldStore'

const DEAD = 0.12

/**
 * Left-thumb virtual stick for walk/strafe on touch devices.
 * Look is handled by dragging the rest of the canvas (ExploreControls).
 */
export function MobileMoveStick() {
  const setTouchMove = useWorldStore((s) => s.setTouchMove)
  const setExploring = useWorldStore((s) => s.setExploring)
  const baseRef = useRef<HTMLDivElement>(null)
  const knobRef = useRef<HTMLDivElement>(null)
  const active = useRef(false)
  const origin = useRef({ x: 0, y: 0 })

  const apply = useCallback(
    (clientX: number, clientY: number) => {
      const base = baseRef.current
      const knob = knobRef.current
      if (!base || !knob) return
      const r = base.getBoundingClientRect()
      const cx = r.left + r.width / 2
      const cy = r.top + r.height / 2
      const max = r.width * 0.38
      let dx = clientX - cx
      let dy = clientY - cy
      const len = Math.hypot(dx, dy) || 1
      if (len > max) {
        dx = (dx / len) * max
        dy = (dy / len) * max
      }
      knob.style.transform = `translate(${dx}px, ${dy}px)`
      let nx = dx / max
      let ny = -dy / max
      if (Math.abs(nx) < DEAD) nx = 0
      if (Math.abs(ny) < DEAD) ny = 0
      setTouchMove(nx, ny)
    },
    [setTouchMove],
  )

  const end = useCallback(() => {
    active.current = false
    setTouchMove(0, 0)
    if (knobRef.current) knobRef.current.style.transform = 'translate(0px, 0px)'
  }, [setTouchMove])

  useEffect(() => {
    const onUp = () => {
      if (active.current) end()
    }
    window.addEventListener('pointerup', onUp)
    window.addEventListener('pointercancel', onUp)
    return () => {
      window.removeEventListener('pointerup', onUp)
      window.removeEventListener('pointercancel', onUp)
      end()
    }
  }, [end])

  return (
    <div
      ref={baseRef}
      className="mobile-stick"
      aria-label="Move"
      onPointerDown={(e) => {
        e.preventDefault()
        e.stopPropagation()
        active.current = true
        setExploring(true)
        origin.current = { x: e.clientX, y: e.clientY }
        baseRef.current?.setPointerCapture(e.pointerId)
        apply(e.clientX, e.clientY)
      }}
      onPointerMove={(e) => {
        if (!active.current) return
        e.preventDefault()
        e.stopPropagation()
        apply(e.clientX, e.clientY)
      }}
      onPointerUp={(e) => {
        e.stopPropagation()
        end()
      }}
    >
      <div ref={knobRef} className="mobile-stick__knob" />
      <span className="mobile-stick__label mono-label">Move</span>
    </div>
  )
}
