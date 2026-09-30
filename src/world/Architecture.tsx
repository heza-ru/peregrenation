import type { ArchPrimitive, SceneManifest } from '../painting/types'
import { assertNotWalkable3DParallax } from './worldMode'

function ArchItem({ item, dimensional }: { item: ArchPrimitive; dimensional: number }) {
  const opacity = Math.min(0.45, (item.opacity ?? 0.15) * Math.max(dimensional, 0.05) * 1.4)
  const color = '#4a3f34'
  const rot = item.rotation ?? [0, 0, 0]

  if (item.type === 'cylinder') {
    return (
      <mesh position={item.position} rotation={rot} castShadow={false}>
        <cylinderGeometry args={[item.radius ?? 0.3, item.radius ?? 0.3, item.height ?? 4, 12]} />
        <meshBasicMaterial color={color} transparent opacity={opacity} depthWrite={false} />
      </mesh>
    )
  }

  if (item.type === 'plane') {
    const size = item.size ?? [10, 10]
    const w = size[0]
    const h = size[1] ?? 10
    return (
      <mesh position={item.position} rotation={rot}>
        <planeGeometry args={[w, h]} />
        <meshBasicMaterial color={color} transparent opacity={opacity} depthWrite={false} />
      </mesh>
    )
  }

  if (item.type === 'box') {
    const size = item.size ?? [1, 1, 1]
    const sx = size[0]
    const sy = size[1] ?? 1
    const sz = size[2] ?? sx * 0.4
    return (
      <mesh position={item.position} rotation={rot}>
        <boxGeometry args={[sx, sy, sz]} />
        <meshBasicMaterial color={color} transparent opacity={opacity} depthWrite={false} />
      </mesh>
    )
  }

  const _never: never = item.type
  void _never
  return null
}

export function Architecture({
  manifest,
  dimensional,
}: {
  manifest: SceneManifest
  dimensional: number
}) {
  assertNotWalkable3DParallax(manifest.paintingId, 'Architecture(ghost)')

  return (
    <group>
      {manifest.architecture.map((item) => (
        <ArchItem key={item.id} item={item} dimensional={dimensional} />
      ))}
    </group>
  )
}
