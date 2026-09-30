import { assets } from '../data'
import { lockScroll } from '../motion/scroll'

const NUMERALS = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X'] as const

/** Chapter backdrops: warmed while the hero loads so scrolling never waits on them. */
const CHAPTER_BACKDROPS = [assets.annunciation, assets.explorePoster, assets.cranach, assets.pontormo]

const MIN_FIRST_VISIT_MS = 2200
const MIN_REPEAT_MS = 700
/** Slow networks still get the doorway; the hero finishes loading behind the iris. */
const MAX_WAIT_MS = 8000
const SEEN_KEY = 'pg:doorway-seen'

let resolveDone: () => void = () => {}
const done = new Promise<void>((resolve) => {
  resolveDone = resolve
})

let progress = 0

/** Resolves when the doorway is revealed (immediately on routes without a preloader). */
export function whenPreloaded(): Promise<void> {
  return done
}

/** Displayed load progress 0–1, for the WebGL void behind the loader. */
export function preloaderProgress(): number {
  return progress
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
  let numeral = -1
  let raf = 0

  const render = (p: number) => {
    progress = p
    root.style.setProperty('--p', p.toFixed(4))
    const n = Math.min(NUMERALS.length - 1, Math.floor(p * NUMERALS.length))
    if (n !== numeral && countEl) {
      numeral = n
      countEl.textContent = NUMERALS[n]
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
        // Hero entrance plays as the scene forms (or the iris opens), not behind the veil.
        html.classList.remove('is-preloading')
        html.classList.add('is-revealing')
        lockScroll(false)
        resolveDone()
        window.setTimeout(
          () => {
            root.remove()
            html.classList.remove('has-preloader')
          },
          reduced ? 600 : 1500,
        )
        window.setTimeout(() => html.classList.remove('is-revealing'), reduced ? 600 : 3200)
      },
      reduced ? 150 : 480,
    )
  }

  const tick = (now: number) => {
    const dt = Math.min(0.1, Math.max(0, (now - last) / 1000))
    last = now
    // Never outrun the minimum hold, so a warm cache still fills the porthole evenly.
    const paced = 1 - Math.pow(1 - Math.min(1, now / minMs), 2)
    const target = Math.min(paced, ready ? 1 : settled / tasks.length)
    // Catch up to real progress quickly; creep toward the next step so a big layer never looks frozen.
    const ceiling = Math.min(paced, ready ? 1 : Math.min(0.96, target + 0.55 / tasks.length))
    const behind = shown < target
    const rate = behind ? 5 : 0.45
    shown += ((behind ? target : ceiling) - shown) * (1 - Math.exp(-dt * rate))
    render(shown)

    if (ready && shown > 0.99 && now >= minMs) {
      finish()
      return
    }
    raf = requestAnimationFrame(tick)
  }
  raf = requestAnimationFrame(tick)

  window.addEventListener('pagehide', () => cancelAnimationFrame(raf), { once: true })
}
