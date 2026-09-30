/** One-shot transition fronts (ring bursts) requested by the DOM, drawn by the scene canvas */
export type Burst = { x: number; y: number; born: number; strength: number }

export const MAX_BURSTS = 4

export const fxBus: { bursts: Burst[] } = { bursts: [] }

/** Ignite a ring front at a viewport point (CSS px). */
export function burst(x: number, y: number, strength = 1) {
  fxBus.bursts.push({ x, y, born: performance.now(), strength })
  if (fxBus.bursts.length > MAX_BURSTS) fxBus.bursts.shift()
}
