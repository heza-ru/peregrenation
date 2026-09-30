import { useEffect } from 'react'
import { addFrame, FramePriority } from './frameLoop'

export const FINE_POINTER = '(hover: hover) and (pointer: fine)'

/** Phones, tablets, and the narrow layout. OR-list: any one match takes the lite path. */
export const LITE_UI = '(hover: none), (pointer: coarse), (max-width: 899px)'

export function isLiteUi(): boolean {
  return window.matchMedia(LITE_UI).matches
}

type Spring = { x: number; y: number; tx: number; ty: number }
type Magnet = Spring & { el: HTMLElement; inner: HTMLElement | null; strength: number }
type Tilt = Spring & { el: HTMLElement; max: number; g: number; tg: number; gx: number; gy: number }

const SETTLED = 0.02

/**
 * Delegated pointer physics for `[data-magnetic]` (pulls toward the cursor, value = strength)
 * and `[data-tilt]` (3D lean + glare, value = max degrees). Magnets write the `translate`
 * property and tilts write `transform`, so neither fights the reveal or hover styles.
 */
export function useInteractions(reduced: boolean) {
  useEffect(() => {
    if (reduced || !window.matchMedia(FINE_POINTER).matches) return

    const magnets = new Map<HTMLElement, Magnet>()
    const tilts = new Map<HTMLElement, Tilt>()
    let hotMagnet: Magnet | null = null
    let hotTilt: Tilt | null = null

    const release = () => {
      if (hotMagnet) {
        hotMagnet.tx = 0
        hotMagnet.ty = 0
        hotMagnet = null
      }
      if (hotTilt) {
        hotTilt.tx = 0
        hotTilt.ty = 0
        hotTilt.tg = 0
        hotTilt = null
      }
    }

    const onMove = (e: PointerEvent) => {
      if (e.pointerType !== 'mouse') return
      const target = e.target instanceof Element ? e.target : null

      const mEl = target?.closest<HTMLElement>('[data-magnetic]') ?? null
      if (hotMagnet && hotMagnet.el !== mEl) {
        hotMagnet.tx = 0
        hotMagnet.ty = 0
        hotMagnet = null
      }
      if (mEl) {
        let m = magnets.get(mEl)
        if (!m) {
          m = {
            el: mEl,
            inner: mEl.querySelector<HTMLElement>('[data-magnetic-inner]'),
            strength: Number(mEl.dataset.magnetic) || 0.3,
            x: 0,
            y: 0,
            tx: 0,
            ty: 0,
          }
          magnets.set(mEl, m)
        }
        const r = mEl.getBoundingClientRect()
        m.tx = (e.clientX - (r.left - m.x + r.width / 2)) * m.strength
        m.ty = (e.clientY - (r.top - m.y + r.height / 2)) * m.strength
        hotMagnet = m
      }

      const tEl = target?.closest<HTMLElement>('[data-tilt]') ?? null
      if (hotTilt && hotTilt.el !== tEl) {
        hotTilt.tx = 0
        hotTilt.ty = 0
        hotTilt.tg = 0
        hotTilt = null
      }
      if (tEl) {
        let t = tilts.get(tEl)
        if (!t) {
          t = { el: tEl, max: Number(tEl.dataset.tilt) || 3, x: 0, y: 0, tx: 0, ty: 0, g: 0, tg: 0, gx: 50, gy: 50 }
          tilts.set(tEl, t)
        }
        const r = tEl.getBoundingClientRect()
        const nx = ((e.clientX - r.left) / r.width) * 2 - 1
        const ny = ((e.clientY - r.top) / r.height) * 2 - 1
        t.tx = nx
        t.ty = ny
        t.tg = 1
        t.gx = ((e.clientX - r.left) / r.width) * 100
        t.gy = ((e.clientY - r.top) / r.height) * 100
        hotTilt = t
      }
    }

    const onOut = (e: PointerEvent) => {
      if (!e.relatedTarget) release()
    }

    const removeFrame = addFrame((_, dt) => {
      const kIn = 1 - Math.exp(-dt * 11)
      const kOut = 1 - Math.exp(-dt * 6)

      for (const m of magnets.values()) {
        const k = m === hotMagnet ? kIn : kOut
        m.x += (m.tx - m.x) * k
        m.y += (m.ty - m.y) * k
        if (m !== hotMagnet && Math.abs(m.x) < SETTLED && Math.abs(m.y) < SETTLED) {
          m.el.style.translate = ''
          if (m.inner) m.inner.style.translate = ''
          magnets.delete(m.el)
          continue
        }
        m.el.style.translate = `${m.x.toFixed(2)}px ${m.y.toFixed(2)}px`
        if (m.inner) m.inner.style.translate = `${(m.x * 0.4).toFixed(2)}px ${(m.y * 0.4).toFixed(2)}px`
      }

      for (const t of tilts.values()) {
        const k = t === hotTilt ? kIn * 0.7 : kOut
        t.x += (t.tx - t.x) * k
        t.y += (t.ty - t.y) * k
        t.g += (t.tg - t.g) * k
        if (t !== hotTilt && Math.abs(t.x) < SETTLED * 0.1 && Math.abs(t.y) < SETTLED * 0.1 && t.g < 0.01) {
          t.el.style.transform = ''
          t.el.style.removeProperty('--glare')
          t.el.style.removeProperty('--nx')
          t.el.style.removeProperty('--ny')
          tilts.delete(t.el)
          continue
        }
        t.el.style.transform = `perspective(1400px) rotateX(${(-t.y * t.max).toFixed(3)}deg) rotateY(${(t.x * t.max).toFixed(3)}deg)`
        t.el.style.setProperty('--nx', t.x.toFixed(3))
        t.el.style.setProperty('--ny', t.y.toFixed(3))
        t.el.style.setProperty('--glare', t.g.toFixed(3))
        t.el.style.setProperty('--gx', `${t.gx.toFixed(1)}%`)
        t.el.style.setProperty('--gy', `${t.gy.toFixed(1)}%`)
      }
    }, FramePriority.state)

    window.addEventListener('pointermove', onMove, { passive: true })
    document.addEventListener('pointerout', onOut)
    return () => {
      removeFrame()
      window.removeEventListener('pointermove', onMove)
      document.removeEventListener('pointerout', onOut)
      for (const m of magnets.values()) {
        m.el.style.translate = ''
        if (m.inner) m.inner.style.translate = ''
      }
      for (const t of tilts.values()) t.el.style.transform = ''
    }
  }, [reduced])
}
