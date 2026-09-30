import { useTexture } from '@react-three/drei'
import { useLayoutEffect, useMemo } from 'react'
import * as THREE from 'three'
import { paintingAssetUrl } from '../painting/paths'
import type { SceneEntity, SceneManifest } from '../painting/types'
import { entityWorldPosition } from '../painting/uvPlacement'
import { assertNotWalkable3DParallax } from './worldMode'

type CutoutEntity = SceneEntity & { mask: string }

function EntityCutout({
  entity,
  manifest,
  dimensional,
}: {
  entity: CutoutEntity
  manifest: SceneManifest
  dimensional: number
}) {
  const paintingUrl = paintingAssetUrl(manifest.paintingId, 'painting.jpg')
  const maskUrl = paintingAssetUrl(manifest.paintingId, entity.mask)
  const map = useTexture(paintingUrl)
  const alphaMap = useTexture(maskUrl)

  useLayoutEffect(() => {
    map.colorSpace = THREE.SRGBColorSpace
    map.minFilter = THREE.LinearFilter
    map.magFilter = THREE.LinearFilter
    alphaMap.minFilter = THREE.LinearFilter
    alphaMap.magFilter = THREE.LinearFilter
    map.needsUpdate = true
  }, [map, alphaMap])

  const { planeWidth, planeHeight } = manifest.composition
  const w = entity.cutoutWidth ?? planeWidth * 0.12
  const h = entity.cutoutHeight ?? planeHeight * 0.28
  const [x, y, z] = entityWorldPosition(entity, manifest.composition)
  const opacity = Math.min(1, dimensional * 1.15)

  return (
    <mesh position={[x, y, z + 0.02]} scale={entity.scale}>
      <planeGeometry args={[w, h]} />
      <meshBasicMaterial
        map={map}
        alphaMap={alphaMap}
        transparent
        opacity={opacity}
        depthWrite={false}
        toneMapped={false}
      />
    </mesh>
  )
}

/**
 * Plane-stuck cutouts for legacy layered worlds only.
 * Walkable 3D halls (Athens) must use AthensFigures (inflated 3D figures) — this path throws if misrouted.
 */
export function EntityCutouts({
  manifest,
  dimensional,
}: {
  manifest: SceneManifest
  dimensional: number
}) {
  assertNotWalkable3DParallax(manifest.paintingId, 'EntityCutouts')

  const withMasks = useMemo(
    () =>
      manifest.entities.filter((e): e is CutoutEntity => Boolean(e.interactive && e.mask)),
    [manifest.entities],
  )

  if (!withMasks.length || dimensional < 0.05) return null

  return (
    <group>
      {withMasks.map((entity) => (
        <EntityCutout key={entity.id} entity={entity} manifest={manifest} dimensional={dimensional} />
      ))}
    </group>
  )
}
