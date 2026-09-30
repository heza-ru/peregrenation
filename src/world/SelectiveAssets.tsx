import { useGLTF } from '@react-three/drei'
import { Suspense } from 'react'
import type { SceneAsset, SceneManifest } from '../painting/types'
import { paintingAssetUrl } from '../painting/paths'

function GlbAsset({ asset, paintingId }: { asset: SceneAsset; paintingId: string }) {
  const url = asset.url.startsWith('http') || asset.url.startsWith('/')
    ? asset.url
    : paintingAssetUrl(paintingId, asset.url)
  const gltf = useGLTF(url)
  const scale = asset.scale ?? [1, 1, 1]
  const rotation = asset.rotation ?? [0, 0, 0]

  return (
    <primitive
      object={gltf.scene.clone()}
      position={asset.position}
      rotation={rotation}
      scale={scale}
    />
  )
}

/** Selective GLB props from manifest.assets — no-op when empty. */
export function SelectiveAssets({ manifest }: { manifest: SceneManifest }) {
  const assets = manifest.assets ?? []
  if (!assets.length) return null

  return (
    <Suspense fallback={null}>
      <group>
        {assets.map((asset) => (
          <GlbAsset key={asset.id} asset={asset} paintingId={manifest.paintingId} />
        ))}
      </group>
    </Suspense>
  )
}
