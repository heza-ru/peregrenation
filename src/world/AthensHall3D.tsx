import { useEffect, useMemo } from 'react'
import * as THREE from 'three'
import { ATHENS_HALL } from './athensHallConfig'
import type { AthensScene } from './athensScene'
import { useSceneTextures } from './sceneTextures'

export { sceneAssetUrls, useSceneTextures } from './sceneTextures'

/** The dark the visitor stands in before stepping through the entrance. */
export const ATHENS_VOID = '#0b0907'

function SkyDome() {
  const material = useMemo(
    () =>
      new THREE.ShaderMaterial({
        side: THREE.BackSide,
        depthWrite: false,
        toneMapped: false,
        uniforms: {
          top: { value: new THREE.Color('#4f73b4') },
          horizon: { value: new THREE.Color('#dde5ef') },
          voidColor: { value: new THREE.Color(ATHENS_VOID) },
        },
        vertexShader: /* glsl */ `
          varying vec3 vDir;
          varying float vWorldZ;
          void main() {
            vDir = normalize(position);
            vWorldZ = (modelMatrix * vec4(position, 1.0)).z;
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          }
        `,
        fragmentShader: /* glsl */ `
          uniform vec3 top;
          uniform vec3 horizon;
          uniform vec3 voidColor;
          varying vec3 vDir;
          varying float vWorldZ;
          void main() {
            float t = smoothstep(-0.02, 0.5, vDir.y);
            vec3 sky = mix(horizon, top, t);
            // the painted sky belongs to the hall: towards the entrance it deepens into the void
            gl_FragColor = vec4(mix(sky, voidColor, smoothstep(-40.0, 60.0, vWorldZ)), 1.0);
            #include <colorspace_fragment>
          }
        `,
      }),
    [],
  )
  useEffect(() => () => material.dispose(), [material])
  return (
    <mesh position={[0, 0, -20]} material={material} renderOrder={-1}>
      <sphereGeometry args={[150, 32, 16]} />
    </mesh>
  )
}

/** Baked, unlit architecture; out on the landing only the painting's spilled light remains. */
function archMaterial(map: THREE.Texture): THREE.MeshBasicMaterial {
  const m = new THREE.MeshBasicMaterial({ map, alphaTest: 0.5, side: THREE.DoubleSide, toneMapped: false })
  const fadeFrom = ATHENS_HALL.portalZ + 0.1
  m.onBeforeCompile = (shader) => {
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nvarying float vWorldZ;')
      .replace(
        '#include <project_vertex>',
        '#include <project_vertex>\nvWorldZ = (modelMatrix * vec4(transformed, 1.0)).z;',
      )
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', '#include <common>\nvarying float vWorldZ;')
      .replace(
        '#include <map_fragment>',
        `#include <map_fragment>
        diffuseColor.rgb *= exp(-0.45 * max(vWorldZ - ${fadeFrom.toFixed(2)}, 0.0));`,
      )
  }
  return m
}

/**
 * Walkable School of Athens architecture. Every wall, step, vault and floor carries its own
 * texture baked offline from the 17k-pixel fresco (painter's-eye bake with occlusion, hidden
 * texels filled from the hall's symmetry and repeating bays), so surfaces stay coherent and
 * detailed from any position — no runtime projection.
 */
export function AthensHall3D({ paintingId, scene }: { paintingId: string; scene: AthensScene }) {
  const pages = useSceneTextures(paintingId, scene.index.pages.arch)

  const materials = useMemo(() => pages.map(archMaterial), [pages])
  useEffect(() => () => materials.forEach((m) => m.dispose()), [materials])

  return (
    <group>
      {scene.arch.map((m) => (
        <mesh key={m.page} geometry={m.geometry} material={materials[m.page]} />
      ))}
      <SkyDome />
    </group>
  )
}
