import { useEffect, useRef } from 'react'
import { whenPreloaded } from '../boot/preloader'
import { assets } from '../data'
import { usePrefersReducedMotion } from '../hooks/useMotion'
import { addFrame, FramePriority } from '../motion/frameLoop'
import { burst } from '../scene/fxBus'
import { heroBus } from '../scene/heroBus'
import { boundaryProgress, HERO_LAYERS, REACH_RADIUS, SPARK } from '../scene/scenes'
import { CompositionGrid, SparkField } from './MotionChrome'
import { Pill } from './Pill'
import { SiteHeader } from './SiteHeader'
import { Words } from './Words'

type Plane = {
  key: keyof typeof assets.parallax
  depth: number
  dolly: number
  bob?: number
  drift?: number
}

const PLANES: readonly Plane[] = [
  { key: 'far', depth: 0.04, dolly: 0.06 },
  { key: 'clouds', depth: 0.12, dolly: 0.12, drift: 26 },
  { key: 'landscape', depth: 0.24, dolly: 0.2 },
  { key: 'rock', depth: 0.6, dolly: 0.42 },
  { key: 'adam', depth: 0.6, dolly: 0.42 },
  { key: 'god', depth: 0.82, dolly: 0.62, bob: 7 },
]

const TILT_X = 58
const TILT_Y = 30
/** Viewports of runway left once the dolly completes — the ignite window of the next chapter */
const IGNITE_LEAD = 0.4

const clamp01 = (t: number) => Math.min(1, Math.max(0, t))
const easeScrub = (t: number) => 1 - Math.pow(1 - t, 1.65)
const easeOutExpo = (t: number) => (t >= 1 ? 1 : 1 - Math.pow(2, -10 * t))

type HeroProps = {
  onBegin?: () => void
}

export function Hero({ onBegin }: HeroProps) {
  const reduced = usePrefersReducedMotion()
  const sectionRef = useRef<HTMLElement>(null)
  const planeRefs = useRef<(HTMLDivElement | null)[]>([])
  const copyRef = useRef<HTMLDivElement>(null)
  const ctaRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const section = sectionRef.current
    if (!section) return
    if (reduced) {
      section.style.setProperty('--dolly', '0')
      section.style.setProperty('--ignite', '0')
      section.style.setProperty('--spark', '0.4')
      return
    }

    const pointer = { x: 0, y: 0, active: false }
    const cur = { x: 0, y: 0, dolly: 0, ignite: 0, spark: 0, ctaX: 0, ctaY: 0, touch: 0 }
    let start = performance.now()
    let alive = true
    // The dolly-in intro should play as the doorway opens, not behind the preloader.
    void whenPreloaded().then(() => {
      if (alive) start = performance.now()
    })
    let visible = true
    let hover = false
    const imgs = planeRefs.current.map((el) => el?.querySelector('img') ?? null)
    const pill = ctaRef.current?.querySelector<HTMLElement>('.pill') ?? null
    const onReach = () => {
      hover = true
    }
    const onRelease = () => {
      hover = false
    }
    const onSpark = () => {
      const r = pill?.getBoundingClientRect()
      if (r) burst(r.left + r.width * 0.41, r.top - 4, 1.35)
    }
    pill?.addEventListener('click', onSpark)
    pill?.addEventListener('pointerenter', onReach)
    pill?.addEventListener('pointerleave', onRelease)
    pill?.addEventListener('focus', onReach)
    pill?.addEventListener('blur', onRelease)

    const onPointer = (e: PointerEvent) => {
      if (e.pointerType !== 'mouse') return
      pointer.x = (e.clientX / window.innerWidth) * 2 - 1
      pointer.y = (e.clientY / window.innerHeight) * 2 - 1
      pointer.active = true
    }
    const onLeave = () => {
      pointer.active = false
    }

    const frame = (now: number, dt: number) => {
      if (!visible) return
      const t = (now - start) / 1000
      const vh = window.innerHeight
      const rect = section.getBoundingClientRect()
      const dollyRun = Math.max(1, rect.height - vh * (1 + IGNITE_LEAD))
      const dollyTarget = clamp01(-rect.top / dollyRun)
      const igniteTarget = boundaryProgress(rect.bottom, vh, 'ignite')

      const tx = pointer.active ? pointer.x : Math.sin(t * 0.28) * 0.28
      const ty = pointer.active ? pointer.y : Math.cos(t * 0.22) * 0.16
      const kPointer = 1 - Math.exp(-dt * 2.6)
      const kScroll = 1 - Math.exp(-dt * 3.2)
      const kIgnite = 1 - Math.exp(-dt * 7)
      cur.x += (tx - cur.x) * kPointer
      cur.y += (ty - cur.y) * kPointer
      cur.dolly += (dollyTarget - cur.dolly) * kScroll
      cur.ignite += (igniteTarget - cur.ignite) * kIgnite

      const dx = pointer.x * 0.5 + 0.5 - SPARK.x
      const dy = (pointer.y * 0.5 + 0.5 - SPARK.y) * (vh / window.innerWidth)
      const sparkTarget = pointer.active ? clamp01(1 - Math.hypot(dx, dy) / 0.3) : 0.4
      cur.spark += (sparkTarget - cur.spark) * kPointer

      const dolly = easeScrub(cur.dolly)
      const ignite = cur.ignite
      const intro = easeOutExpo(clamp01(t / 2.4))

      // Adam and God yearn toward the CTA out of phase; hovering it makes them strain for contact
      cur.touch += ((hover ? 1 : 0) - cur.touch) * (1 - Math.exp(-dt * (hover ? 4.5 : 2.2)))
      const settle = clamp01((t - 1.1) / 1.6) * clamp01(1 - dolly * 2.2) * clamp01(1 - ignite * 5)
      const strain = Math.sin(t * 13) * 0.02 * cur.touch
      const yearn = (phase: number) => 0.52 + 0.2 * Math.sin(t * 0.8 + phase)
      const reachOf = (key: Plane['key']) => {
        const idle = yearn(key === 'god' ? 1.3 : 0)
        return (idle + (0.94 - idle) * cur.touch + (key === 'god' ? -strain : strain)) * settle
      }
      const pr = pill && settle > 0 ? pill.getBoundingClientRect() : null
      const vw = document.documentElement.clientWidth
      section.style.setProperty('--touch', (cur.touch * settle).toFixed(3))

      PLANES.forEach((plane, i) => {
        const d = plane.depth
        const driftX = plane.drift ? Math.sin(t * 0.055) * plane.drift : 0
        const bobY = plane.bob ? Math.sin(t * 0.85) * plane.bob : 0
        const x = -cur.x * TILT_X * d + driftX
        const y = -cur.y * TILT_Y * d + bobY + (1 - d) * dolly * 72 - d * dolly * 28
        const scale =
          1 +
          dolly * plane.dolly +
          dolly * 0.1 +
          ignite * (0.03 + d * 0.06) +
          (1 - intro) * (0.16 + d * 0.08)
        const state =
          heroBus.planes[i] ?? (heroBus.planes[i] = { x: 0, y: 0, scale: 1, pullX: 0, pullY: 0 })
        state.x = x
        state.y = y
        state.scale = scale
        state.pullX = 0
        state.pullY = 0

        const tip = HERO_LAYERS[i]?.tip
        const img = imgs[i]
        if (tip && pr && img?.naturalWidth) {
          // Fingertip on screen: same cover fit + transform the canvas applies to this plane
          const bw = 1.2 * vw
          const bh = 1.2 * vh
          const cover = Math.max(bw / img.naturalWidth, bh / img.naturalHeight)
          const rw = img.naturalWidth * cover
          const rh = img.naturalHeight * cover
          const ox = SPARK.x * bw
          const oy = SPARK.y * bh
          const lx = (bw - rw) * SPARK.x + tip[0] * rw
          const ly = (bh - rh) * SPARK.y + tip[1] * rh
          const sx = -0.1 * vw + ox + (lx - ox) * scale + x
          const sy = -0.1 * vh + oy + (ly - oy) * scale + y
          const aimX = pr.left + pr.width * (plane.key === 'god' ? 0.52 : 0.3)
          const aimY = pr.top - 3
          const amt = reachOf(plane.key)
          let px = (aimX - sx) * amt
          let py = (aimY - sy) * amt
          // Past ~⅓ of the falloff radius the liquify pull would fold the arm over itself
          const cap = 0.34 * REACH_RADIUS * rw * scale
          const len = Math.hypot(px, py)
          if (len > cap) {
            px *= cap / len
            py *= cap / len
          }
          state.pullX = px
          state.pullY = py
        }
        const el = planeRefs.current[i]
        if (el) el.style.transform = `translate3d(${x.toFixed(2)}px, ${y.toFixed(2)}px, 0) scale(${scale.toFixed(4)})`
      })

      section.style.setProperty('--dolly', dolly.toFixed(4))
      section.style.setProperty('--ignite', ignite.toFixed(4))
      section.style.setProperty('--spark', cur.spark.toFixed(3))

      const copy = copyRef.current
      if (copy) {
        copy.style.transform = `translate3d(0, ${(-dolly * 140).toFixed(1)}px, 0) scale(${(1 - dolly * 0.22).toFixed(4)})`
        copy.style.opacity = clamp01(1 - dolly * 1.25).toFixed(3)
      }

      // The CTA rides the painting's parallax, then is caught by the ignite and blown away
      const cta = ctaRef.current
      if (cta) {
        const cx = -cur.x * TILT_X * 0.7 + Math.sin(t * 0.6) * 2
        const cy = -cur.y * TILT_Y * 0.7 + Math.cos(t * 0.8) * 3
        cur.ctaX += (cx - cur.ctaX) * kPointer
        cur.ctaY += (cy - cur.ctaY) * kPointer
        const gust = easeOutExpo(clamp01(ignite / 0.22))
        const x = cur.ctaX + gust * 90
        const y = cur.ctaY - dolly * 24 - gust * 140
        const scale = 1 + dolly * 0.16 + gust * 0.12
        cta.style.transform = `translate3d(${x.toFixed(2)}px, ${y.toFixed(2)}px, 0) rotate(${(gust * 18).toFixed(2)}deg) scale(${scale.toFixed(3)})`
        cta.style.opacity = clamp01(1 - gust * 1.1).toFixed(3)
        cta.style.filter = gust > 0.001 ? `blur(${(gust * 5).toFixed(2)}px)` : ''
      }
    }

    const io = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting
    })
    io.observe(section)
    window.addEventListener('pointermove', onPointer, { passive: true })
    document.documentElement.addEventListener('pointerleave', onLeave)
    const removeFrame = addFrame(frame, FramePriority.state)

    return () => {
      alive = false
      removeFrame()
      io.disconnect()
      window.removeEventListener('pointermove', onPointer)
      document.documentElement.removeEventListener('pointerleave', onLeave)
      pill?.removeEventListener('click', onSpark)
      pill?.removeEventListener('pointerenter', onReach)
      pill?.removeEventListener('pointerleave', onRelease)
      pill?.removeEventListener('focus', onReach)
      pill?.removeEventListener('blur', onRelease)
    }
  }, [reduced])

  return (
    <section id="top" ref={sectionRef} className="hero" data-scene="hero">
      <div className="hero__sticky">
        <div className="hero__scene" aria-hidden="true">
          {PLANES.map((plane, i) => (
            <div
              key={plane.key}
              ref={(el) => {
                planeRefs.current[i] = el
              }}
              className={`hero__plane hero__plane--${plane.key}`}
            >
              <img
                src={assets.parallax[plane.key]}
                alt=""
                draggable={false}
                decoding="async"
                loading={i < 2 || plane.key === 'god' || plane.key === 'adam' ? 'eager' : 'lazy'}
                fetchPriority={i === 0 || plane.key === 'god' ? 'high' : 'low'}
                sizes="100vw"
              />
            </div>
          ))}
        </div>

        <div className="hero__glow" aria-hidden="true" />
        <div className="hero__vignette" aria-hidden="true" />
        <CompositionGrid tone="light" />
        <SiteHeader tone="light" onBegin={onBegin} />

        <div ref={copyRef} className="hero__copy">
          <div className="hero__titles">
            <h1>
              <span className="hero__title-line hero__title-line--ital">
                <Words text="Le Voyage" />
              </span>
              <span className="hero__title-line">
                <Words text="des Curiosités" from={2} />
              </span>
            </h1>
            <div className="hero__tagline hero__enter hero__enter--late">
              <svg className="hero__ornament hero__ornament--left" width="56" height="10" viewBox="0 0 56 10" fill="none" stroke="#7A3A22" strokeWidth="1" aria-hidden="true">
                <path d="M0 5 H44" />
                <path d="M50 1 L54 5 L50 9 L46 5 Z" fill="#7A3A22" />
              </svg>
              <p>A journey through worlds of art, knowledge, and wonder.</p>
              <svg className="hero__ornament hero__ornament--right" width="56" height="10" viewBox="0 0 56 10" fill="none" stroke="#7A3A22" strokeWidth="1" aria-hidden="true">
                <path d="M12 5 H56" />
                <path d="M6 1 L10 5 L6 9 L2 5 Z" fill="#7A3A22" />
              </svg>
            </div>
          </div>

          <SparkField />

          <p className="hero__pitch hero__enter hero__enter--last">
            Turn a Renaissance painting into a world you can walk through, and uncover its
            curiosities as you go.
          </p>
        </div>

        <div className="hero__cta-wrap hero__enter hero__enter--cta">
          <div ref={ctaRef} className="hero__cta">
            <Pill
              href="#enter"
              label="Begin the journey"
              tone="light"
              onClick={(e) => {
                e.preventDefault()
                onBegin?.()
              }}
            />
          </div>
        </div>

        <span className="hero__credit">Michelangelo · The Creation of Adam, c. 1512</span>
      </div>
    </section>
  )
}
