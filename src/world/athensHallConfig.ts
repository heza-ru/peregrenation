import { type BoxCollider, resolveWalker } from './walkColliders'

/**
 * School of Athens walkable hall, in metres (y-up, −Z into the fresco).
 *
 * Measured from the fresco: vanishing point px (1017, 760) on the 1920 frame, f = 1600 px,
 * painter's eye 2.87 m above the forecourt at z = 10.3. Four steps (rise 0.25, tread 0.40)
 * climb to the philosophers' platform at 1.0 m. Bay 1 runs z −3.3…−7.7, the domed crossing
 * −7.7…−16.0, bay 2 to −29.5, the far screen wall stands at −32. The ornamental entrance (the
 * real Stanza wall around the lunette) stands at z = portalZ; its opening, seen from the
 * painter's eye, is exactly the fresco's frame. Visitors start on the landing in front of it.
 * Must stay in sync with scripts/pipeline/athens_arch.py.
 */
export const ATHENS_HALL = {
  eyeHeight: 1.7,
  /** A step back from the fresco: the whole ornamental entrance is in view. */
  spawn: { x: 0, y: 1.7, z: 8.8 },
  lookAt: { x: 0, y: 2.9, z: -30 },
  portalZ: 3.0,
  /** Walkable span of the entrance opening at floor level (doorway parapet left, pilaster right). */
  portalOpen: { minX: -2.85, maxX: 3.55 },
  landingEndZ: 10.5,
  stepFronts: [0, -0.4, -0.8, -1.2],
  stepRise: 0.25,
  platformY: 1.0,
  naveHalf: 2.55,
  pierFaceZ: -3.3,
  bay1EndZ: -7.7,
  crossingEndZ: -16.0,
  crossingHalf: 4.2,
  farWallZ: -32,
  hallHalf: 8.6,
  bounds: { minX: -8.3, maxX: 8.3, minZ: -31.6, maxZ: 10.0 },
} as const

export function athensFloorHeight(z: number): number {
  const { stepFronts, stepRise, platformY } = ATHENS_HALL
  if (z > stepFronts[0]) return 0
  for (let i = 1; i < stepFronts.length; i++) {
    if (z > stepFronts[i]) return stepRise * i
  }
  return platformY
}

export type AthensCollider = BoxCollider

const H = ATHENS_HALL
const FAR = 20

function mirroredX(minX: number, maxX: number, minZ: number, maxZ: number): AthensCollider[] {
  return [
    { minX, maxX, minZ, maxZ },
    { minX: -maxX, maxX: -minX, minZ, maxZ },
  ]
}

export const ATHENS_STATIC_COLLIDERS: AthensCollider[] = [
  // Front piers with their pilaster bases, and the first bay's walls
  ...mirroredX(H.naveHalf, FAR, H.bay1EndZ, H.pierFaceZ + 0.3),
  // Crossing: its thin arch walls either side of the nave, and the side walls
  ...mirroredX(H.naveHalf, FAR, H.bay1EndZ - 0.2, H.bay1EndZ),
  ...mirroredX(H.naveHalf, FAR, H.crossingEndZ, H.crossingEndZ + 0.2),
  ...mirroredX(H.crossingHalf, FAR, H.crossingEndZ, H.bay1EndZ),
  // Second bay and the open court
  ...mirroredX(H.naveHalf, FAR, H.farWallZ - 1, H.crossingEndZ),
  // The entrance wall either side of its opening
  { minX: -FAR, maxX: H.portalOpen.minX, minZ: H.portalZ - 0.08, maxZ: H.portalZ + 0.04 },
  { minX: H.portalOpen.maxX, maxX: FAR, minZ: H.portalZ - 0.08, maxZ: H.portalZ + 0.04 },
  // Heraclitus' marble block on the forecourt
  { minX: -0.65, maxX: 0.01, minZ: 0.23, maxZ: 0.83 },
]

let figureColliders: AthensCollider[] = []

export function setAthensFigureColliders(colliders: AthensCollider[]): void {
  figureColliders = colliders
}

/** Push a walker (circle in XZ) out of walls and figures, then clamp to the hall. */
export function resolveAthensPosition(p: { x: number; z: number }, radius = 0.22): void {
  resolveWalker(p, [ATHENS_STATIC_COLLIDERS, figureColliders], ATHENS_HALL.bounds, radius)
}
