import { useTexture } from '@react-three/drei'
import { useFrame, useThree } from '@react-three/fiber'
import { useLayoutEffect, useMemo, useRef } from 'react'
import * as THREE from 'three'
import { resolveLayerTexture } from '../painting/loadManifest'
import { paintingAssetUrl } from '../painting/paths'
import type { SceneLayer, SceneManifest } from '../painting/types'
import { getDeviceProfile } from './deviceProfile'
import { assertNotWalkable3DParallax } from './worldMode'

/** Cap hero painting upload on weak GPUs (gallery thumbs stay separate). */
function limitMapSize(texture: THREE.Texture, maxSize: number): void {
  const img = texture.image as { width?: number; height?: number } | undefined
  if (!img?.width || !img?.height) return
  const maxDim = Math.max(img.width, img.height)
  if (maxDim <= maxSize) return
  const scale = maxSize / maxDim
  const w = Math.max(1, Math.floor(img.width * scale))
  const h = Math.max(1, Math.floor(img.height * scale))
  const canvas = document.createElement('canvas')
  canvas.width = w
  canvas.height = h
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  ctx.drawImage(img as CanvasImageSource, 0, 0, w, h)
  texture.image = canvas
  texture.needsUpdate = true
}

type LayerMeshProps = {
  manifest: SceneManifest
  layer: SceneLayer
  width: number
  height: number
  dimensional: number
  baseCamera: THREE.Vector3
}

function useParallaxGroup(
  dimensional: number,
  layer: SceneLayer,
  baseCamera: THREE.Vector3,
) {
  const group = useRef<THREE.Group>(null)
  const { camera } = useThree()
  const z = layer.z * dimensional
  const parallax = layer.parallax

  useFrame(() => {
    const g = group.current
    if (!g) return
    const dx = (camera.position.x - baseCamera.x) * (1 - parallax)
    const dy = (camera.position.y - baseCamera.y) * (1 - parallax)
    g.position.set(dx, dy, z)
  })

  return group
}

function PlainLayer(props: LayerMeshProps & { heroFade: boolean }) {
  const { manifest, layer, width, height, dimensional, baseCamera, heroFade } = props
  const group = useParallaxGroup(dimensional, layer, baseCamera)
  const url = resolveLayerTexture(manifest, layer)
  const texture = useTexture(url)
  const profile = useMemo(() => getDeviceProfile(), [])

  useLayoutEffect(() => {
    limitMapSize(texture, profile.maxTextureSize)
    texture.colorSpace = THREE.SRGBColorSpace
    texture.generateMipmaps = !profile.lowPower
    texture.minFilter = profile.lowPower ? THREE.LinearFilter : THREE.LinearMipmapLinearFilter
    texture.magFilter = THREE.LinearFilter
    texture.needsUpdate = true
  }, [texture, profile])

  const isHero = layer.hero === true
  const cutout = layer.texture.includes('layers/')
  const opacity = isHero
    ? heroFade
      ? Math.max(0.4, 1 - dimensional * 0.55)
      : 1
    : layer.opacity * dimensional

  return (
    <group ref={group}>
      <mesh>
        <planeGeometry args={[width, height]} />
        <meshBasicMaterial
          map={texture}
          transparent={cutout || (isHero && heroFade)}
          opacity={cutout ? dimensional : opacity}
          toneMapped={false}
          depthWrite={isHero && !heroFade}
        />
      </mesh>
    </group>
  )
}

function MaskedLayer(props: LayerMeshProps & { maskUrl: string }) {
  const { manifest, layer, width, height, dimensional, baseCamera, maskUrl } = props
  const group = useParallaxGroup(dimensional, layer, baseCamera)
  const url = resolveLayerTexture(manifest, layer)
  const texture = useTexture(url)
  const alphaTexture = useTexture(maskUrl)

  useLayoutEffect(() => {
    const profile = getDeviceProfile()
    limitMapSize(texture, profile.maxTextureSize)
    texture.colorSpace = THREE.SRGBColorSpace
    texture.generateMipmaps = !profile.lowPower
    texture.minFilter = profile.lowPower ? THREE.LinearFilter : THREE.LinearMipmapLinearFilter
    texture.magFilter = THREE.LinearFilter
    alphaTexture.minFilter = THREE.LinearFilter
    alphaTexture.magFilter = THREE.LinearFilter
    texture.needsUpdate = true
  }, [texture, alphaTexture])

  const cutout = layer.texture.includes('layers/')
  const opacity = layer.opacity * dimensional

  return (
    <group ref={group}>
      <mesh>
        <planeGeometry args={[width, height]} />
        <meshBasicMaterial
          map={texture}
          alphaMap={alphaTexture}
          transparent
          opacity={cutout ? dimensional : opacity}
          toneMapped={false}
          depthWrite={false}
        />
      </mesh>
    </group>
  )
}

function LayerMesh(props: LayerMeshProps & { heroFade: boolean }) {
  const { manifest, layer } = props
  const isHero = layer.hero === true
  const hasMask = Boolean(layer.mask)
  const cutout = layer.texture.includes('layers/')
  if (!isHero && !hasMask && !cutout) return null

  if (hasMask && layer.mask) {
    const maskUrl = paintingAssetUrl(manifest.paintingId, layer.mask)
    return <MaskedLayer {...props} maskUrl={maskUrl} />
  }
  return <PlainLayer {...props} />
}

export function PaintingLayers({
  manifest,
  dimensional,
  baseCamera,
}: {
  manifest: SceneManifest
  dimensional: number
  baseCamera: THREE.Vector3
}) {
  // Hard ban: School of Athens (and other walkable halls) must never use parallax planes.
  assertNotWalkable3DParallax(manifest.paintingId, 'PaintingLayers')

  const { planeWidth, planeHeight } = manifest.composition
  const sorted = [...manifest.layers].sort((a, b) => a.depthBand - b.depthBand)
  const heroFade = sorted.some(
    (l) => !l.hero && (Boolean(l.mask) || l.texture.includes('layers/')),
  )

  return (
    <group>
      {sorted.map((layer) => (
        <LayerMesh
          key={layer.id}
          manifest={manifest}
          layer={layer}
          width={planeWidth}
          height={planeHeight}
          dimensional={dimensional}
          baseCamera={baseCamera}
          heroFade={heroFade}
        />
      ))}
    </group>
  )
}
