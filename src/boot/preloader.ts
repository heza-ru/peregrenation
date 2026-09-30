import { assets } from '../data'
import { lockScroll } from '../motion/scroll'

const STATUS: readonly (readonly [number, string])[] = [
  [0, 'Stretching the canvas'],
  [0.3, 'Grinding the pigments'],
  [0.62, 'Gilding the frame'],
  [0.9, 'Opening the doorway'],
]

/** Chapter backdrops: warmed while the hero loads so scrolling never waits on them. */
const CHAPTER_BACKDROPS = [assets.annunciation, assets.explorePoster, assets.cranach, assets.pontormo]

const MIN_FIRST_VISIT_MS = 1300
const MIN_REPEAT_MS = 450
/** Slow networks still get the doorway; the hero finishes loading behind the iris. */
const MAX_WAIT_MS = 8000
const SEEN_KEY = 'pg:doorway-seen'

let resolveDone: () => void = () => {}
const done = new Promise<void>((resolve) => {
  resolveDone = resolve
})

/** Resolves when the doorway is revealed (immediately on routes without a preloader). */
export function whenPreloaded(): Promise<void> {
  return done
}

const sleep = (ms: number) => new Promise<void>((r) => window.setTimeout(r, ms))

function decodeImage(src: string): Promise<void> {
  const img = new Image()
  img.decoding = 'async'
  img.src = src
  return img.decode().catch(() => undefined)
}

/** The Google Fonts sheet is injected async, so faces may not be declared yet — poll briefly. */
async function waitForFonts(capMs: number): Promise<void> {
  if (!('fonts' in document)) return
  const faces = ['400 1em "IM Fell French Canon"', 'italic 400 1em "IM Fell French Canon"', '400 1em "IM Fell English SC"']
  const deadline = performance.now() + capMs
  while (performance.now() < deadline) {
    const loaded = await Promise.all(faces.map((f) => document.fonts.load(f).catch(() => [])))
    if (loaded.every((list) => list.length > 0)) return
    await sleep(120)
  }
}

function seenThisSession(): boolean {
  try {
    return sessionStorage.getItem(SEEN_KEY) === '1'
  } catch {
    return false
  }
}

function markSeen() {
  try {
    sessionStorage.setItem(SEEN_KEY, '1')
  } catch {
    /* private mode */
  }
}

export function startPreloader(appMounted: Promise<void>) {
  const html = document.documentElement
  const root = document.getElementById('preloader')
  if (!root || !html.classList.contains('has-preloader')) {
    html.classList.remove('has-preloader', 'is-preloading')
    root?.remove()
    resolveDone()
    return
  }

  const countEl = root.querySelector<HTMLElement>('[data-preloader-count]')
  const statusEl = root.querySelector<HTMLElement>('[data-preloader-status]')
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const minMs = seenThisSession() ? MIN_REPEAT_MS : MIN_FIRST_VISIT_MS

  lockScroll(true)

  const tasks: Promise<void>[] = [...Object.values(assets.parallax).map(decodeImage), waitForFonts(3000)]
  let settled = 0
  tasks.forEach((t) => t.then(() => (settled += 1)))
  const allSettled = Promise.all(tasks).then(() => {
    for (const src of CHAPTER_BACKDROPS) {
      const img = new Image()
      img.fetchPriority = 'low'
      img.src = src
    }
  })

  let ready = false
  void Promise.race([Promise.all([allSettled, appMounted]), sleep(MAX_WAIT_MS)]).then(() => {
    ready = true
  })

  let shown = 0
  let last = performance.now()
  let statusIdx = -1
  let raf = 0

  const render = (p: number) => {
    root.style.setProperty('--p', p.toFixed(4))
    if (countEl) countEl.textContent = String(Math.round(p * 100)).padStart(2, '0')
    let idx = 0
    for (let i = 0; i < STATUS.length; i++) if (p >= STATUS[i][0]) idx = i
    if (idx !== statusIdx && statusEl) {
      statusIdx = idx
      statusEl.textContent = STATUS[idx][1]
    }
  }

  const finish = () => {
    render(1)
    markSeen()
    root.classList.add('is-complete')
    root.setAttribute('aria-busy', 'false')
    window.setTimeout(
      () => {
        root.classList.add('is-leaving')
        // Hero entrance plays as the iris opens, not behind the veil.
        html.classList.remove('is-preloading')
        lockScroll(false)
        resolveDone()
        window.setTimeout(
          () => {
            root.remove()
            html.classList.remove('has-preloader')
          },
          reduced ? 600 : 1500,
        )
      },
      reduced ? 150 : 480,
    )
  }

  const tick = (now: number) => {
    const dt = Math.min(0.1, (now - last) / 1000)
    last = now
    const target = ready ? 1 : settled / tasks.length
    // Catch up to real progress quickly; creep toward the next step so a big layer never looks frozen.
    const ceiling = ready ? 1 : Math.min(0.96, target + 0.55 / tasks.length)
    const behind = shown < target
    const rate = ready ? 6 : behind ? 5 : 0.45
    shown += ((behind || ready ? target : ceiling) - shown) * (1 - Math.exp(-dt * rate))
    render(shown)

    if (ready && shown > 0.995 && now >= minMs) {
      finish()
      return
    }
    raf = requestAnimationFrame(tick)
  }
  raf = requestAnimationFrame(tick)

  window.addEventListener('pagehide', () => cancelAnimationFrame(raf), { once: true })
}
