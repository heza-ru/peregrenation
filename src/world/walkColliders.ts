/** Axis-aligned footprint in the XZ plane (metres). */
export type BoxCollider = { minX: number; maxX: number; minZ: number; maxZ: number }

/** Push a walker (circle in XZ) out of every box, then clamp it to the bounds. */
export function resolveWalker(
  p: { x: number; z: number },
  lists: readonly (readonly BoxCollider[])[],
  bounds: BoxCollider,
  radius: number,
): void {
  for (let pass = 0; pass < 2; pass++) {
    for (const list of lists) {
      for (const c of list) {
        const nx = Math.max(c.minX, Math.min(p.x, c.maxX))
        const nz = Math.max(c.minZ, Math.min(p.z, c.maxZ))
        const dx = p.x - nx
        const dz = p.z - nz
        const d2 = dx * dx + dz * dz
        if (d2 >= radius * radius) continue
        if (d2 > 1e-8) {
          const d = Math.sqrt(d2)
          p.x = nx + (dx / d) * radius
          p.z = nz + (dz / d) * radius
        } else {
          // Centre inside the box: exit through the nearest face
          const exits = [
            [p.x - c.minX + radius, -1, 0],
            [c.maxX - p.x + radius, 1, 0],
            [p.z - c.minZ + radius, 0, -1],
            [c.maxZ - p.z + radius, 0, 1],
          ] as const
          const [dist, ex, ez] = exits.reduce((a, b) => (b[0] < a[0] ? b : a))
          p.x += ex * dist
          p.z += ez * dist
        }
      }
    }
  }
  p.x = Math.min(bounds.maxX, Math.max(bounds.minX, p.x))
  p.z = Math.min(bounds.maxZ, Math.max(bounds.minZ, p.z))
}
