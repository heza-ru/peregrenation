/** Worlds that must render as walkable 3D halls — never PaintingLayers parallax. */
export const WALKABLE_3D_WORLD_IDS = ['school-of-athens', 'arnolfini-portrait'] as const

export type Walkable3DWorldId = (typeof WALKABLE_3D_WORLD_IDS)[number]

/** How a shipped world is explored in `/world/:id`. */
export type WorldKind = '2d' | '3d'

export function isWalkable3DWorld(paintingId: string): paintingId is Walkable3DWorldId {
  return (WALKABLE_3D_WORLD_IDS as readonly string[]).includes(paintingId)
}

export function worldKindOf(paintingId: string): WorldKind {
  return isWalkable3DWorld(paintingId) ? '3d' : '2d'
}

/** Call before any parallax / layered-plane path. */
export function assertNotWalkable3DParallax(paintingId: string, where: string): void {
  if (isWalkable3DWorld(paintingId)) {
    throw new Error(
      `[${where}] Refusing parallax/2.5D for "${paintingId}". Walkable worlds render as 3D rooms only.`,
    )
  }
}
