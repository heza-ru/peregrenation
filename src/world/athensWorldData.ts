import type { AthensCollider } from './athensHallConfig'

/** Shape of data/paintings/school-of-athens/world3d.json (scripts/pipeline/build_athens_world3d.py). */
export type AthensFigure = {
  id: string
  tier: 'near' | 'platform' | 'statue'
  crowd: boolean
  center: [number, number, number]
  /** Standing footprint in hall metres (XZ). */
  collider: AthensCollider
}

export type AthensWorldData = {
  version: number
  paintingId: string
  camera: { f: number; cx: number; cy: number; eyeY: number; eyeZ: number; width: number; height: number }
  figures: AthensFigure[]
  anchors: Record<string, [number, number, number]>
}

export function parseAthensWorld(text: string): AthensWorldData {
  const data = JSON.parse(text) as AthensWorldData
  if (data.version !== 2 || !Array.isArray(data.figures) || typeof data.anchors !== 'object') {
    throw new Error('world3d.json is not a v2 Athens world (rebuild with build_athens_world3d.py)')
  }
  return data
}
