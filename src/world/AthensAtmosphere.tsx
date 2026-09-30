import { useEffect, useMemo } from 'react'
import * as THREE from 'three'
import { athensFloorHeight } from './athensHallConfig'
import type { AthensWorldData } from './athensWorldData'

function contactShadowTexture(): THREE.CanvasTexture {
  const c = document.createElement('canvas')
  c.width = c.height = 128
  const g = c.getContext('2d')!
  const grad = g.createRadialGradient(64, 64, 0, 64, 64, 64)
  grad.addColorStop(0, 'rgba(0,0,0,1)')
  grad.addColorStop(0.45, 'rgba(0,0,0,0.6)')
  grad.addColorStop(1, 'rgba(0,0,0,0)')
  g.fillStyle = grad
  g.fillRect(0, 0, 128, 128)
  return new THREE.CanvasTexture(c)
}

/** Soft contact shadow under every standing figure, so each one sits on the stone. */
function ContactShadows({ world }: { world: AthensWorldData }) {
  const texture = useMemo(contactShadowTexture, [])
  const material = useMemo(
    () =>
      new THREE.MeshBasicMaterial({
        map: texture,
        transparent: true,
        opacity: 0.55,
        depthWrite: false,
        polygonOffset: true,
        polygonOffsetFactor: -2,
        toneMapped: false,
      }),
    [texture],
  )
  useEffect(
    () => () => {
      texture.dispose()
      material.dispose()
    },
    [texture, material],
  )
  const spots = useMemo(
    () =>
      world.figures
        .filter((f) => f.tier !== 'statue')
        .map((f) => {
          const { minX, maxX, minZ, maxZ } = f.collider
          const x = (minX + maxX) / 2
          const z = (minZ + maxZ) / 2
          return { id: f.id, x, z, y: athensFloorHeight(z) + 0.006, w: (maxX - minX) * 1.5 + 0.3, d: (maxZ - minZ) * 2.2 + 0.25 }
        }),
    [world],
  )
  return (
    <group>
      {spots.map((s) => (
        <mesh key={s.id} position={[s.x, s.y, s.z]} rotation-x={-Math.PI / 2} scale={[s.w, s.d, 1]} material={material}>
          <planeGeometry args={[1, 1]} />
        </mesh>
      ))}
    </group>
  )
}

/** Light hall atmosphere — contact shadows only (no sparkles / post stack; those cost FPS). */
export function AthensAtmosphere({ world }: { world: AthensWorldData }) {
  return <ContactShadows world={world} />
}
