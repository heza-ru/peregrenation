import type { SceneEntity, SceneManifest } from './types'

/** Map painting UV (0–1, top-left origin) onto the hero plane in world space. */
export function uvToPlanePosition(
  u: number,
  v: number,
  composition: SceneManifest['composition'],
  /** Small push toward camera so pins sit in front of the fresco */
  zOffset = 0.12,
): [number, number, number] {
  const { planeWidth, planeHeight } = composition
  const x = (u - 0.5) * planeWidth
  const y = (0.5 - v) * planeHeight
  return [x, y, zOffset]
}

export function entityWorldPosition(
  entity: SceneEntity & { promptPoint?: [number, number] },
  composition: SceneManifest['composition'],
): [number, number, number] {
  const uv = entity.promptPoint
  if (uv) {
    const relief = Math.max(0, 4 - (entity.depth ?? 1)) * 0.04
    // Nudge pins slightly above the annotated point so cards sit over heads / focal points,
    // not pasted onto faces (UV origin is top-left → smaller v is higher on the painting).
    const lift =
      entity.type === 'figure' ? 0.04 : entity.type === 'object' ? 0.02 : 0.03
    return uvToPlanePosition(uv[0], Math.max(0, uv[1] - lift), composition, 0.14 + relief)
  }
  return entity.position
}
