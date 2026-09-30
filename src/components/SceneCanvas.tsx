import { useEffect, useRef } from 'react'
import { addFrame, FramePriority } from '../motion/frameLoop'
import { burst, fxBus } from '../scene/fxBus'
import { heroBus } from '../scene/heroBus'
import { SceneEngine, TRAIL_MAX, type LayerDraw, type TrailPoint } from '../scene/SceneEngine'
import {
  boundaryProgress,
  isSceneId,
  isVariant,
  REACH_RADIUS,
  SCENES,
  SPARK,
  variantMode,
  type SceneId,
  type Variant,
} from '../scene/scenes'

type ChapterBox = {
  el: HTMLElement
  scene: SceneId
  variant: Variant
  top: number
  height: number
  progress: number
}

type TailSample = { x: number; y: number; r: number; born: number }

/** Cursor tail tuning, CSS px and ms */
const TAIL_STEP = 5
const TAIL_R = 3
const TAIL_R_FAST = 8
const TAIL_LIFE = 560
const HEAD_R = 4.5
const HEAD_IDLE = 1800
/** Must match BURST_LIFE in the composite shader, seconds */
const BURST_LIFE = 1.5
const INTERACTIVE = 'a, button, input, textarea, select, label, video, [role="button"], [data-cursor]'
/** Places where the painting itself shows through, so a click can visibly ignite it */
const OPEN_CANVAS = '.hero, .chapter__stage'

const clamp01 = (t: number) => Math.min(1, Math.max(0, t))
const smoothstep = (a: number, b: number, t: number) => {
  const x = clamp01((t - a) / (b - a))
  return x * x * (3 - 2 * x)
}

function measure(): ChapterBox[] {
  const y = window.scrollY
  return Array.from(document.querySelectorAll<HTMLElement>('[data-scene]')).flatMap((el) => {
    const scene = el.dataset.scene
    const variant = el.dataset.variant ?? 'ignite'
    if (!isSceneId(scene) || !isVariant(variant)) return []
    const r = el.getBoundingClientRect()
    return [{ el, scene, variant, top: r.top + y, height: r.height, progress: 0 }]
  })
}

/**
 * Fixed WebGL backdrop behind every chapter. Each chapter's painting is drawn offscreen
 * and the composite pass burns one into the next as chapter boundaries scroll past.
 * Chapter headings get `--in` (0 → 1) from the same timeline, with or without WebGL.
 */
export function SceneCanvas({ reduced }: { reduced: boolean }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || reduced) return

    const root = document.documentElement
    const engine = SceneEngine.create(canvas)
    let chapters = measure()
    let dirty = false
    let live = false
    let paperEl: HTMLElement | null = null
    const start = performance.now()
    const pointer = { x: 0, y: 0, tx: 0, ty: 0 }

    const remeasure = () => {
      dirty = true
    }
    const ro = new ResizeObserver(remeasure)
    ro.observe(document.body)
    chapters.forEach((c) => ro.observe(c.el))
    window.addEventListener('resize', remeasure)
    // Viewport-unit sections can shift without any observer firing (mobile toolbars, svh)
    const poll = window.setInterval(remeasure, 500)

    const onPointer = (e: PointerEvent) => {
      if (e.pointerType !== 'mouse') return
      pointer.tx = (e.clientX / window.innerWidth) * 2 - 1
      pointer.ty = (e.clientY / window.innerHeight) * 2 - 1
    }
    window.addEventListener('pointermove', onPointer, { passive: true })

    const tail = { x: 0, y: 0, lastMove: -Infinity, head: 0, samples: [] as TailSample[] }
    const onTrail = (e: PointerEvent) => {
      const now = performance.now()
      const last = tail.samples.at(-1)
      const dist = last ? Math.hypot(e.clientX - last.x, e.clientY - last.y) : Infinity
      tail.x = e.clientX
      tail.y = e.clientY
      tail.lastMove = now
      if (dist < TAIL_STEP) return
      const speed = last && now > last.born ? (dist / (now - last.born)) * 1000 : 0
      tail.samples.push({ x: e.clientX, y: e.clientY, r: TAIL_R + Math.min(speed * 0.008, TAIL_R_FAST), born: now })
      if (tail.samples.length > TRAIL_MAX - 1) tail.samples.shift()
    }
    const onTrailLeave = () => {
      tail.lastMove = -Infinity
    }
    const onIgnite = (e: PointerEvent) => {
      if (e.button !== 0 || !(e.target instanceof Element)) return
      if (e.target.closest(INTERACTIVE) || !e.target.closest(OPEN_CANVAS)) return
      burst(e.clientX, e.clientY, e.pointerType === 'mouse' ? 0.85 : 0.65)
    }
    window.addEventListener('pointermove', onTrail, { passive: true })
    window.addEventListener('pointerdown', onIgnite, { passive: true })
    document.documentElement.addEventListener('pointerleave', onTrailLeave)

    const trailFrame = (now: number, dt: number): TrailPoint[] => {
      while (tail.samples.length && now - tail.samples[0].born > TAIL_LIFE) tail.samples.shift()
      const idle = now - tail.lastMove > HEAD_IDLE
      tail.head += ((idle ? 0 : 1) - tail.head) * (1 - Math.exp(-dt * (idle ? 3 : 9)))
      const pts = tail.samples.map((s) => {
        const life = 1 - (now - s.born) / TAIL_LIFE
        return { x: s.x, y: s.y, r: s.r * Math.pow(life, 0.7), life }
      })
      if (tail.head > 0.01) pts.push({ x: tail.x, y: tail.y, r: HEAD_R * tail.head, life: tail.head })
      return pts
    }

    if (engine) {
      for (const def of Object.values(SCENES)) {
        for (const layer of def.layers) {
          engine.load(layer.src).catch((err) => console.warn('[scene] texture failed', layer.src, err))
        }
      }
    }

    const cssSize = () => [canvas.clientWidth || window.innerWidth, canvas.clientHeight || window.innerHeight] as const

    const sceneLayers = (ch: ChapterBox, w: number, h: number, y: number): LayerDraw[] => {
      const def = SCENES[ch.scene]
      if (ch.scene === 'hero') {
        const box = [-0.1 * w, -0.1 * h, 1.2 * w, 1.2 * h] as const
        const origin = [SPARK.x * box[2], SPARK.y * box[3]] as const
        return def.layers.map((layer, i) => {
          const plane = heroBus.planes[i] ?? { x: 0, y: 0, scale: 1, pullX: 0, pullY: 0 }
          return {
            src: layer.src,
            box,
            focal: def.focal,
            origin,
            tx: plane.x,
            ty: plane.y,
            scale: plane.scale,
            shadow: !!layer.shadow,
            reach: layer.tip
              ? { tip: layer.tip, pull: [plane.pullX, plane.pullY] as const, radius: REACH_RADIUS }
              : undefined,
          }
        })
      }
      const local = clamp01((y - (ch.top - h)) / (ch.height + h))
      const box = [0, 0, w, h] as const
      return def.layers.map((layer) => ({
        src: layer.src,
        box,
        focal: def.focal,
        origin: [def.focal[0] * w, def.focal[1] * h] as const,
        tx: -pointer.x * 14,
        ty: (0.5 - local) * 56 - pointer.y * 9,
        scale: 1.06 + local * 0.14,
        shadow: !!layer.shadow,
      }))
    }

    const dimFor = (ch: ChapterBox, y: number, h: number) =>
      ch.scene === 'hero' ? 0 : 0.26 + 0.46 * smoothstep(0.35, 1.1, (y - ch.top) / h)

    const removeFrame = addFrame((now, dt) => {
      if (dirty) {
        const prev = chapters
        chapters = measure()
        chapters.forEach((c, i) => (c.progress = prev[i]?.progress ?? 0))
        dirty = false
      }
      if (!chapters.length) return

      const [w, h] = cssSize()
      const y = window.scrollY
      const k = 1 - Math.exp(-dt * 7)
      const kp = 1 - Math.exp(-dt * 2.4)
      pointer.x += (pointer.tx - pointer.x) * kp
      pointer.y += (pointer.ty - pointer.y) * kp

      let idx = 0
      let p = 0
      for (let i = 1; i < chapters.length; i++) {
        const ch = chapters[i]
        const raw = boundaryProgress(ch.top - y, h, ch.variant)
        ch.progress += (raw - ch.progress) * k
        if (Math.abs(raw - ch.progress) < 1e-4) ch.progress = raw
        ch.el.style.setProperty('--in', ch.progress.toFixed(4))
        ch.el.style.setProperty('--lift', `${Math.min(2 * h, Math.max(0, ch.top - y)).toFixed(1)}px`)
        if (ch.progress > 0) {
          idx = i
          p = ch.progress
        }
      }

      if (!engine) return
      engine.resize(w, h)

      const to = chapters[idx]
      const from = p < 1 && idx > 0 ? chapters[idx - 1] : to
      const fromDef = SCENES[from.scene]
      const toDef = SCENES[to.scene]
      const transitioning = from !== to

      if (!live) {
        if (!engine.isReady(fromDef.layers.map((l) => l.src))) return
        live = true
        root.classList.add('gl-scene')
      }

      paperEl ??= document.querySelector<HTMLElement>('[data-paper]')
      const pr = paperEl?.getBoundingClientRect()
      const paper = pr && pr.bottom > -200 && pr.top < h + 200 ? ([pr.top, pr.bottom] as const) : null

      engine.drawScene(0, fromDef.bg, sceneLayers(from, w, h, y))
      if (transitioning) engine.drawScene(1, toDef.bg, sceneLayers(to, w, h, y))
      engine.composite({
        progress: transitioning ? p : 0,
        time: (now - start) / 1000,
        mode: variantMode(to.variant),
        origin: [SPARK.x, 1 - SPARK.y],
        seed: idx * 13.37,
        dimA: dimFor(from, y, h),
        dimB: dimFor(to, y, h),
        voidTint: toDef.void,
        paper,
        trail: trailFrame(now, dt),
        bursts: fxBus.bursts.flatMap((b) => {
          const age = (now - b.born) / 1000
          return age < BURST_LIFE ? [{ x: b.x, y: b.y, age, strength: b.strength }] : []
        }),
      })
      fxBus.bursts = fxBus.bursts.filter((b) => now - b.born < BURST_LIFE * 1000)
    }, FramePriority.render)

    return () => {
      removeFrame()
      window.clearInterval(poll)
      ro.disconnect()
      window.removeEventListener('resize', remeasure)
      window.removeEventListener('pointermove', onPointer)
      window.removeEventListener('pointermove', onTrail)
      window.removeEventListener('pointerdown', onIgnite)
      document.documentElement.removeEventListener('pointerleave', onTrailLeave)
      root.classList.remove('gl-scene')
      engine?.dispose()
      // Drop the canvas node so Chromium releases the compositor surface promptly.
      try {
        canvas.width = 1
        canvas.height = 1
        canvas.remove()
      } catch {
        /* ignore */
      }
    }
  }, [reduced])

  return <canvas ref={canvasRef} className="scene-canvas" aria-hidden="true" />
}
