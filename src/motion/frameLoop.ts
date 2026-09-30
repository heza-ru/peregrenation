/**
 * One requestAnimationFrame for the whole page. Callbacks run in priority order
 * (smooth scroll → scene state → WebGL render) so everything reads the same scroll
 * position in the same frame.
 */
export type FrameCallback = (time: number, dt: number) => void

type Entry = { cb: FrameCallback; priority: number }

const entries: Entry[] = []
let raf = 0
let last = 0

const tick = (time: number) => {
  raf = requestAnimationFrame(tick)
  const dt = last ? Math.min(0.05, (time - last) / 1000) : 1 / 60
  last = time
  for (const e of entries) e.cb(time, dt)
}

export const FramePriority = {
  scroll: 0,
  state: 10,
  render: 20,
} as const

export function addFrame(cb: FrameCallback, priority: number): () => void {
  const entry = { cb, priority }
  entries.push(entry)
  entries.sort((a, b) => a.priority - b.priority)
  if (!raf) {
    last = 0
    raf = requestAnimationFrame(tick)
  }
  return () => {
    const i = entries.indexOf(entry)
    if (i >= 0) entries.splice(i, 1)
    if (!entries.length && raf) {
      cancelAnimationFrame(raf)
      raf = 0
    }
  }
}
