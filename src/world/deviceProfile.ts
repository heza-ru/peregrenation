/**
 * Coarse device tier for walkable worlds — phones / weak GPUs need fewer textures,
 * cheaper materials, and a lower pixel ratio or they OOM / freeze on Arnolfini-scale scenes.
 */
export type DeviceProfile = {
  /** Touch-first phone / tablet (or coarse pointer). */
  touchPrimary: boolean
  /** Prefer the lite render path (cheaper shaders, capped textures, no FX). */
  lowPower: boolean
  /** Max canvas DPR. */
  dprMax: number
  /** Cap atlas edge length before GPU upload (px). */
  maxTextureSize: number
  /** Anisotropic filtering samples. */
  anisotropy: number
}

function matchTouch(): boolean {
  if (typeof window === 'undefined') return false
  return window.matchMedia('(hover: none), (pointer: coarse)').matches
}

/** Prefer lite path on phones, Save-Data, low RAM, or weak CPU — never on desktop GPUs with headroom. */
function detectLowPower(touchPrimary: boolean): boolean {
  if (typeof navigator === 'undefined') return touchPrimary
  const mem = (navigator as Navigator & { deviceMemory?: number }).deviceMemory
  const cores = navigator.hardwareConcurrency ?? 8
  const conn = (navigator as Navigator & { connection?: { saveData?: boolean; effectiveType?: string } })
    .connection
  if (conn?.saveData) return true
  if (conn?.effectiveType === 'slow-2g' || conn?.effectiveType === '2g') return true
  if (touchPrimary) return true
  if (typeof mem === 'number' && mem > 0 && mem <= 4) return true
  if (cores > 0 && cores <= 2) return true
  return false
}

let cached: DeviceProfile | null = null

/** Snapshot once per page load — worlds remount often; detecting every frame is wasteful. */
export function getDeviceProfile(): DeviceProfile {
  if (cached) return cached
  const touchPrimary = matchTouch()
  const lowPower = detectLowPower(touchPrimary)
  cached = {
    touchPrimary,
    lowPower,
    dprMax: lowPower ? 1 : 1.5,
    maxTextureSize: lowPower ? 1024 : 2048,
    anisotropy: lowPower ? 1 : 4,
  }
  return cached
}

export function resetDeviceProfileCache(): void {
  cached = null
}
