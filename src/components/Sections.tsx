import {
  useEffect,
  useRef,
  useState,
  type ChangeEvent,
  type CSSProperties,
  type DragEvent,
  type PointerEvent,
  type RefObject,
} from 'react'
import { assets, curiosities, exportFormats, galleryWorldKind, galleryWorks } from '../data'
import { usePrefersReducedMotion } from '../hooks/useMotion'
import { addFrame, FramePriority } from '../motion/frameLoop'
import { StarIcon } from './Icons'
import { Pill } from './Pill'
import { Words } from './Words'

/** Underdrawing lens — decode the second bitmap only after first hover (24× gallery). */
function GalleryFrame({
  src,
  alt,
  kind,
  eager,
}: {
  src: string
  alt: string
  kind: '2d' | '3d' | null
  eager: boolean
}) {
  const [lensArmed, setLensArmed] = useState(false)
  return (
    <div className="gallery__frame" onPointerEnter={() => setLensArmed(true)}>
      <img
        src={src}
        alt={alt}
        loading={eager ? 'eager' : 'lazy'}
        decoding="async"
        fetchPriority={eager ? 'high' : 'auto'}
      />
      {kind && (
        <span className={`gallery__kind gallery__kind--${kind}`}>
          {kind === '3d' ? '3D hall' : '2D wander'}
        </span>
      )}
      <div className="gallery__lens" aria-hidden="true">
        {lensArmed ? <img src={src} alt="" loading="lazy" decoding="async" /> : null}
      </div>
      <span className="gallery__ember" aria-hidden="true" />
    </div>
  )
}

export function BuildSection() {
  return (
    <section className="build reveal">
      <div className="build__sticky">
        <div className="build__intro">
          <div className="build__copy">
            <span className="eyebrow" data-reveal-child>
              Build
            </span>
            <h2>
              <Words text="One painting in." /> <em><Words text="A whole world out." from={3} /></em>
            </h2>
          </div>
          <p className="build__lede" data-reveal-child>
            Add any Renaissance painting. We read the perspective the artist drew, split the
            scene into depth, and imagine what lies beyond the frame.
          </p>
        </div>
        <div className="media-panel media-panel--mask" data-reveal-child data-tilt="2.2">
          <video
            src={assets.buildVideo}
            poster={assets.buildPoster}
            autoPlay
            muted
            loop
            playsInline
            preload="none"
          />
          <span className="chip chip--ghost media-panel__left layer">Painting</span>
          <span className="chip chip--gold media-panel__right layer">World</span>
          <div className="status-card layer layer--deep">
            <span className="mono-label">Vanishing point located</span>
            <span className="status-card__value">5 depth planes · loggia, hills, town</span>
          </div>
        </div>
      </div>
    </section>
  )
}

type DropState = 'idle' | 'over' | 'received'

function dropCopy(state: DropState): { desk: string; mobile: string } {
  switch (state) {
    case 'idle':
      return { desk: 'Drop a scan or search by title', mobile: 'Take a photo or upload' }
    case 'over':
      return { desk: 'Release to open the frame', mobile: 'Release to open the frame' }
    case 'received':
      return { desk: 'Reading the perspective…', mobile: 'Reading the perspective…' }
    default: {
      const never: never = state
      return never
    }
  }
}

const hasFiles = (e: DragEvent) => Array.from(e.dataTransfer.types).includes('Files')

function DropTray() {
  const [state, setState] = useState<DropState>('idle')
  const depth = useRef(0)

  useEffect(() => {
    if (state !== 'received') return
    const id = window.setTimeout(() => setState('idle'), 2800)
    return () => window.clearTimeout(id)
  }, [state])

  const onDragEnter = (e: DragEvent<HTMLDivElement>) => {
    if (!hasFiles(e)) return
    e.preventDefault()
    depth.current += 1
    setState('over')
  }
  const onDragOver = (e: DragEvent<HTMLDivElement>) => {
    if (hasFiles(e)) e.preventDefault()
  }
  const onDragLeave = () => {
    depth.current = Math.max(0, depth.current - 1)
    if (depth.current === 0) setState((s) => (s === 'over' ? 'idle' : s))
  }
  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    if (!hasFiles(e)) return
    e.preventDefault()
    depth.current = 0
    setState('received')
  }
  const onPick = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) setState('received')
    e.target.value = ''
  }

  const copy = dropCopy(state)

  return (
    <div
      className={`drop-tray layer drop-tray--${state}`}
      onDragEnter={onDragEnter}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
    >
      <img src={assets.cranach} alt="" />
      <img className="drop-tray__desk-only" src={assets.pontormo} alt="" />
      <label className="drop-tray__zone" data-cursor="Upload">
        <input type="file" accept="image/*" className="sr-only" onChange={onPick} />
        <svg className="drop-tray__icon" width="18" height="18" viewBox="0 0 22 22" fill="none" stroke="#A33A1C" strokeWidth="1.8" aria-hidden="true">
          <path d="M11 15 V3 M6 8 L11 3 L16 8 M3 15 V19 H19 V15" />
        </svg>
        <span className="drop-tray__desk" key={`d-${state}`}>
          {copy.desk}
        </span>
        <span className="drop-tray__mobile" key={`m-${state}`}>
          {copy.mobile}
        </span>
      </label>
    </div>
  )
}

const KEYS: Record<string, readonly [number, number]> = {
  w: [0, -1],
  a: [-1, 0],
  s: [0, 1],
  d: [1, 0],
}

/** WASD (or pressing the keycaps) nudges the camera; the reticle trails the pointer. */
function useExploreControls(ref: RefObject<HTMLDivElement | null>) {
  useEffect(() => {
    const panel = ref.current
    if (!panel) return
    let inView = false
    const held = new Set<string>()
    const caps = Array.from(panel.querySelectorAll<HTMLElement>('[data-key]'))

    const sync = () => {
      let vx = 0
      let vy = 0
      held.forEach((k) => {
        vx += KEYS[k][0]
        vy += KEYS[k][1]
      })
      panel.style.setProperty('--vx', String(vx))
      panel.style.setProperty('--vy', String(vy))
      panel.classList.toggle('is-moving', held.size > 0)
      caps.forEach((cap) => cap.classList.toggle('is-down', held.has(cap.dataset.key ?? '')))
    }

    const onKeyDown = (e: KeyboardEvent) => {
      const k = e.key.toLowerCase()
      if (!inView || !(k in KEYS) || e.metaKey || e.ctrlKey || e.altKey) return
      if (e.target instanceof HTMLElement && e.target.closest('input, textarea, [contenteditable]')) return
      held.add(k)
      sync()
    }
    const onKeyUp = (e: KeyboardEvent) => {
      if (held.delete(e.key.toLowerCase())) sync()
    }
    const clear = () => {
      held.clear()
      sync()
    }
    const onCapDown = (e: globalThis.PointerEvent) => {
      const k = (e.currentTarget as HTMLElement).dataset.key
      if (!k) return
      held.add(k)
      sync()
    }
    const onCapUp = () => clear()

    const io = new IntersectionObserver(
      ([entry]) => {
        inView = entry.intersectionRatio > 0.35
        if (!inView) clear()
      },
      { threshold: [0, 0.35, 1] },
    )
    io.observe(panel)
    window.addEventListener('keydown', onKeyDown)
    window.addEventListener('keyup', onKeyUp)
    window.addEventListener('blur', clear)
    caps.forEach((cap) => cap.addEventListener('pointerdown', onCapDown))
    window.addEventListener('pointerup', onCapUp)
    return () => {
      io.disconnect()
      window.removeEventListener('keydown', onKeyDown)
      window.removeEventListener('keyup', onKeyUp)
      window.removeEventListener('blur', clear)
      caps.forEach((cap) => cap.removeEventListener('pointerdown', onCapDown))
      window.removeEventListener('pointerup', onCapUp)
    }
  }, [ref])
}

const onLookMove = (e: PointerEvent<HTMLDivElement>) => {
  const el = e.currentTarget
  const r = el.getBoundingClientRect()
  el.style.setProperty('--lx', (((e.clientX - r.left) / r.width) * 2 - 1).toFixed(3))
  el.style.setProperty('--ly', (((e.clientY - r.top) / r.height) * 2 - 1).toFixed(3))
}
const onLookLeave = (e: PointerEvent<HTMLDivElement>) => {
  e.currentTarget.style.setProperty('--lx', '0')
  e.currentTarget.style.setProperty('--ly', '0')
}

export function LearnSection() {
  const [active, setActive] = useState(0)
  const [auto, setAuto] = useState(true)
  const learnRef = useRef<HTMLDivElement>(null)
  const exploreRef = useRef<HTMLDivElement>(null)
  const fact = curiosities[active]
  useExploreControls(exploreRef)

  useEffect(() => {
    const panel = learnRef.current
    if (!panel) return
    const io = new IntersectionObserver(([entry]) => panel.classList.toggle('is-live', entry.isIntersecting), {
      threshold: 0.45,
    })
    io.observe(panel)
    return () => io.disconnect()
  }, [])

  const pick = (i: number) => {
    setActive(i)
    setAuto(false)
  }

  return (
    <section className="bento reveal">
      <div
        ref={learnRef}
        className="learn-panel"
        data-reveal-child
        style={
          {
            '--fx': fact.x,
            '--fy': fact.y,
            '--fx-m': fact.xMobile,
            '--fy-m': fact.yMobile,
          } as CSSProperties
        }
      >
        <img src={assets.annunciation} alt="Cima da Conegliano, The Annunciation" />
        <div className="learn-panel__shade" />
        <div className="learn-panel__intro">
          <span className="eyebrow">Learn as you wander</span>
          <h3>
            <Words text="Every corner" /> <em><Words text="holds a curiosity." from={2} /></em>
          </h3>
        </div>

        {curiosities.map((c, i) => (
          <button
            key={c.id}
            type="button"
            className={`marker${i === active ? ' is-active' : ''}`}
            style={
              {
                '--mx': c.x,
                '--my': c.y,
                '--mx-m': c.xMobile,
                '--my-m': c.yMobile,
                '--i': i,
              } as CSSProperties
            }
            aria-label={`Curiosity ${c.id}: ${c.title}`}
            aria-pressed={i === active}
            onClick={() => pick(i)}
          >
            {c.id}
          </button>
        ))}

        <div className="fact-card layer" key={fact.id}>
          <div className="fact-card__meta">
            <span className="label-rust">Curiosité {fact.id} of 3</span>
            <span className="mono-label">{auto ? 'Wandering' : 'Tap a marker'}</span>
          </div>
          <span className="fact-card__title">
            <Words text={fact.title} />
          </span>
          <span className="fact-card__text">{fact.text}</span>
          {auto && (
            <span
              className="fact-card__timer"
              aria-hidden="true"
              onAnimationEnd={() => setActive((a) => (a + 1) % curiosities.length)}
            />
          )}
        </div>
      </div>

      <div className="bento__side">
        <div className="add-panel" data-reveal-child data-tilt="2.4">
          <img
            src={assets.littaMadonna}
            alt="Leonardo da Vinci, The Litta Madonna"
            className="add-panel__img"
          />
          <div className="add-panel__shade" />
          <div className="add-panel__intro">
            <span className="eyebrow">Add a painting</span>
            <h3>
              <Words text="Bring your" /> <em><Words text="favourite masterpiece." from={2} /></em>
            </h3>
          </div>
          <DropTray />
        </div>

        <div
          ref={exploreRef}
          className="explore-panel"
          data-reveal-child
          data-tilt="2.4"
          onPointerMove={onLookMove}
          onPointerLeave={onLookLeave}
        >
          <video
            src={assets.exploreVideo}
            poster={assets.explorePoster}
            autoPlay
            muted
            loop
            playsInline
            preload="none"
          />
          <div className="explore-panel__shade" />
          <div className="chip chip--ghost explore-panel__count layer">
            <StarIcon size={12} fill="#C9A24A" />
            Curiosities 3 / 12
          </div>
          <svg
            className="explore-panel__reticle"
            width="36"
            height="36"
            viewBox="0 0 36 36"
            fill="none"
            stroke="#EFE6D6"
            strokeWidth="1.5"
            aria-hidden="true"
          >
            <circle cx="18" cy="18" r="8" />
            <path d="M18 2 V10 M18 26 V34 M2 18 H10 M26 18 H34" />
          </svg>
          <div className="explore-panel__foot layer">
            <div>
              <span className="eyebrow">Explore</span>
              <h3>
                <Words text="Walk the" /> <em><Words text="artist’s imagination." from={2} /></em>
              </h3>
              <span className="explore-panel__hint">Drag to look around · tap to walk</span>
            </div>
            <div className="wasd" aria-hidden="true">
              <span />
              <span data-key="w">W</span>
              <span />
              <span data-key="a">A</span>
              <span data-key="s">S</span>
              <span data-key="d">D</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v))

export function GallerySection() {
  const reduced = usePrefersReducedMotion()
  const sectionRef = useRef<HTMLElement>(null)
  const pinRef = useRef<HTMLDivElement>(null)
  const railRef = useRef<HTMLDivElement>(null)
  const progressRef = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    const section = sectionRef.current
    const pin = pinRef.current
    const rail = railRef.current
    const progress = progressRef.current
    if (!section || !pin || !rail || !progress || reduced) return

    const cards = Array.from(rail.querySelectorAll<HTMLElement>('.gallery__card'))
    const imgs = cards.map((c) => Array.from(c.querySelectorAll<HTMLElement>('img')))
    let boxes: { left: number; width: number }[] = []
    let railLeft = 0
    let maxScroll = 0
    const measure = () => {
      maxScroll = Math.max(0, rail.scrollWidth - pin.clientWidth)
      section.style.height = `${pin.offsetHeight + maxScroll}px`
      boxes = cards.map((c) => ({ left: c.offsetLeft, width: c.offsetWidth }))
      railLeft = (rail.parentElement?.getBoundingClientRect().left ?? 0) + window.scrollX
    }
    measure()
    const ro = new ResizeObserver(measure)
    ro.observe(pin)
    ro.observe(rail)

    let lastX = 0
    let skew = 0
    const remove = addFrame((_, dt) => {
      const rect = section.getBoundingClientRect()
      const vh = window.innerHeight
      if (rect.bottom < -vh || rect.top > vh * 2) return
      const run = Math.max(1, section.offsetHeight - vh)
      const p = clamp(-rect.top / run, 0, 1)
      const x = -p * maxScroll

      const v = (x - lastX) / Math.max(dt, 1 / 240)
      lastX = x
      skew += (clamp(v * 0.0016, -3.2, 3.2) - skew) * (1 - Math.exp(-dt * 7))
      if (Math.abs(skew) < 0.001) skew = 0

      rail.style.transform = `translate3d(${x.toFixed(2)}px, 0, 0) skewX(${skew.toFixed(3)}deg)`
      progress.style.transform = `scaleX(${p.toFixed(4)})`

      const vw = pin.clientWidth
      boxes.forEach((b, i) => {
        const center = railLeft + b.left + x + b.width / 2
        const rel = clamp((center - vw / 2) / vw, -1, 1)
        const shift = `${(-rel * 6).toFixed(2)}% 0`
        imgs[i]?.forEach((img) => (img.style.translate = shift))
      })
    }, FramePriority.state)

    return () => {
      remove()
      ro.disconnect()
      section.style.height = ''
      rail.style.transform = ''
      imgs.flat().forEach((img) => img.style.removeProperty('translate'))
    }
  }, [reduced])

  useEffect(() => {
    const rail = railRef.current
    if (!rail) return
    const onLens = (e: globalThis.PointerEvent) => {
      if (!(e.target instanceof Element)) return
      const frame = e.target.closest<HTMLElement>('.gallery__frame')
      if (!frame) return
      const r = frame.getBoundingClientRect()
      frame.style.setProperty('--lx', `${(e.clientX - r.left).toFixed(1)}px`)
      frame.style.setProperty('--ly', `${(e.clientY - r.top).toFixed(1)}px`)
    }
    rail.addEventListener('pointermove', onLens, { passive: true })
    return () => rail.removeEventListener('pointermove', onLens)
  }, [])

  return (
    <section ref={sectionRef} className={`gallery reveal${reduced ? ' gallery--static' : ''}`}>
      <div ref={pinRef} className="gallery__pin">
        <div className="gallery__inner">
          <div className="gallery__head">
            <h2>
              <Words text="Choose your" /> <em><Words text="voyage" from={2} /></em>
            </h2>
            <a href="#gallery" className="gallery__browse link-draw" data-reveal-child>
              Browse public-domain works →
            </a>
          </div>
          <div className="gallery__track">
            <div ref={railRef} className="gallery__rail">
              {galleryWorks.map((work, i) => {
                const kind = galleryWorldKind(work)
                return (
                <a
                  key={work.id}
                  href={`#w-${work.id}`}
                  className={`gallery__card gallery__card--${work.widthClass}`}
                  data-reveal-child
                  data-cursor="View"
                  style={{ '--reveal-delay': `${180 + i * 90}ms` } as CSSProperties}
                >
                  <GalleryFrame src={work.src} alt={work.alt} kind={kind} eager={i < 3} />
                  <span className="gallery__meta">
                    <span className="gallery__title">{work.title}</span>
                    <span className="gallery__artist">
                      {work.artist} · {work.year}
                    </span>
                  </span>
                </a>
                )
              })}
            </div>
          </div>
          <div className="gallery__progress" aria-hidden="true">
            <span ref={progressRef} />
          </div>
        </div>
      </div>
    </section>
  )
}

export function ExportSection() {
  return (
    <section className="export reveal">
      <div className="export__media" data-reveal-child>
        <img src={assets.lutePlayer} alt="Caravaggio, The Lute Player" />
      </div>
      <div className="export__copy">
        <span className="eyebrow" data-reveal-child>
          Export
        </span>
        <h2>
          <Words text="Take the world" /> <em><Words text="anywhere." from={3} /></em>
        </h2>
        <p data-reveal-child>
          Keep exploring in a headset, a game engine or a browser. Every curiosity you found
          travels with the world.
        </p>
        <div className="export__formats" data-reveal-child>
          {exportFormats.map((fmt, i) => (
            <span
              key={fmt}
              className={fmt === 'WebXR link' ? 'chip chip--accent' : 'chip chip--outline'}
              style={{ '--ci': i } as CSSProperties}
            >
              {fmt}
            </span>
          ))}
        </div>
      </div>
    </section>
  )
}

export function CtaFooter({ onBegin }: { onBegin?: () => void }) {
  return (
    <section className="cta reveal">
      <div className="cta__row">
        <h2>
          <Words text="Your voyage begins" /> <em><Words text="with one painting." from={3} /></em>
        </h2>
        <div className="cta__action" data-reveal-child>
          <Pill
            href="#enter"
            label="Begin a world"
            tone="accent"
            onClick={(e) => {
              e.preventDefault()
              onBegin?.()
            }}
          />
        </div>
      </div>
      <footer className="site-footer" data-reveal-child>
        <div className="site-footer__brand">
          <span className="site-footer__name">Pérégrination</span>
          <span className="site-footer__tag">
            Le Voyage des Curiosités · A journey through worlds of art, knowledge, and wonder.
          </span>
        </div>
        <span className="site-footer__note">Paintings shown are in the public domain</span>
        <div className="site-footer__links">
          <a href="#terms" className="link-draw">
            Terms
          </a>
          <a href="#privacy" className="link-draw">
            Privacy
          </a>
          <span>© 2026</span>
        </div>
      </footer>
    </section>
  )
}
