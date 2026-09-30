import { assets } from '../data'

export type SceneId = 'hero' | 'build' | 'learn' | 'export' | 'begin'

/** How a chapter's scene takes over from the previous one */
export type Variant = 'ignite' | 'rise' | 'paper' | 'diagonal'

export type SceneLayer = {
  src: string
  /** Soft drop shadow under cut-out figures */
  shadow?: boolean
  /** Fingertip in texture uv; the arm around it can bend to reach for the CTA */
  tip?: readonly [number, number]
}

/** Reach falloff, as a fraction of the rendered layer width (≈ forearm + hand) */
export const REACH_RADIUS = 0.115

export type SceneDef = {
  layers: readonly SceneLayer[]
  /** object-position of the painting (0–1, top-left origin) */
  focal: readonly [number, number]
  /** Fill behind the layers while textures load */
  bg: readonly [number, number, number]
  /** Nebula tint of the starfield void when this scene is arriving */
  void: readonly [number, number, number]
}

/** Hero layers must stay in the same order as the planes in Hero.tsx */
export const HERO_LAYERS: readonly SceneLayer[] = [
  { src: assets.parallax.far },
  { src: assets.parallax.clouds },
  { src: assets.parallax.landscape },
  { src: assets.parallax.rock },
  { src: assets.parallax.adam, shadow: true, tip: [0.4641, 0.427] },
  { src: assets.parallax.god, shadow: true, tip: [0.4762, 0.418] },
]

/** Gap between the fingertips, in viewport fractions (top-left origin) */
export const SPARK = { x: 0.47, y: 0.42 } as const

export const SCENES: Record<SceneId, SceneDef> = {
  hero: {
    layers: HERO_LAYERS,
    focal: [SPARK.x, SPARK.y],
    bg: [0.25, 0.42, 0.55],
    void: [0.1, 0.09, 0.2],
  },
  build: {
    layers: [{ src: assets.annunciation }],
    focal: [0.5, 0.36],
    bg: [0.16, 0.12, 0.09],
    void: [0.1, 0.09, 0.2],
  },
  learn: {
    layers: [{ src: assets.explorePoster }],
    focal: [0.5, 0.45],
    bg: [0.12, 0.14, 0.12],
    void: [0.05, 0.1, 0.16],
  },
  export: {
    layers: [{ src: assets.cranach }],
    focal: [0.5, 0.35],
    bg: [0.08, 0.07, 0.04],
    void: [0.16, 0.08, 0.04],
  },
  begin: {
    layers: [{ src: assets.pontormo }],
    focal: [0.5, 0.3],
    bg: [0.12, 0.07, 0.06],
    void: [0.13, 0.06, 0.11],
  },
}

/** Scroll window of a transition, in viewports of the incoming chapter's top edge */
const WINDOWS: Record<Variant, readonly [start: number, end: number]> = {
  ignite: [1.4, 0.15],
  rise: [1.15, 0.1],
  paper: [1.0, 0.15],
  diagonal: [1.15, 0.1],
}

/** 0 → 1 as the incoming chapter's top travels through its variant's window */
export function boundaryProgress(nextTop: number, vh: number, variant: Variant) {
  const [a, b] = WINDOWS[variant]
  const t = (a * vh - nextTop) / ((a - b) * vh)
  return Math.min(1, Math.max(0, t))
}

/** Composite shader mode for a variant */
export function variantMode(variant: Variant): number {
  switch (variant) {
    case 'ignite':
      return 0
    case 'rise':
    case 'paper':
      return 1
    case 'diagonal':
      return 2
    default: {
      const never: never = variant
      return never
    }
  }
}

export function isSceneId(v: string | undefined): v is SceneId {
  return v !== undefined && v in SCENES
}

export function isVariant(v: string | undefined): v is Variant {
  return v !== undefined && v in WINDOWS
}
