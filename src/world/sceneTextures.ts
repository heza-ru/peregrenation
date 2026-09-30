import { useTexture } from '@react-three/drei'
import { useThree } from '@react-three/fiber'
import { useMemo } from 'react'
import * as THREE from 'three'
import { paintingAssetUrl } from '../painting/paths'
import { getDeviceProfile } from './deviceProfile'

export function sceneAssetUrls(paintingId: string, files: string[]): string[] {
  return files.map((f) => paintingAssetUrl(paintingId, `scene/${f}`))
}

/** Shrink oversized atlases before upload so mid-tier phones don't OOM. */
function limitTextureSize(texture: THREE.Texture, maxSize: number): void {
  const img = texture.image as
    | HTMLImageElement
    | HTMLCanvasElement
    | ImageBitmap
    | { width: number; height: number; close?: () => void }
    | undefined
  if (!img || !('width' in img) || !img.width || !img.height) return
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
  if (typeof (img as ImageBitmap).close === 'function') {
    try {
      ;(img as ImageBitmap).close()
    } catch {
      /* ignore */
    }
  }
  texture.image = canvas
  texture.needsUpdate = true
}

export function useSceneTextures(paintingId: string, files: string[]): THREE.Texture[] {
  const { gl } = useThree()
  const urls = useMemo(() => sceneAssetUrls(paintingId, files), [paintingId, files])
  const profile = useMemo(() => getDeviceProfile(), [])
  return useTexture(urls, (loaded) => {
    const list = Array.isArray(loaded) ? loaded : [loaded]
    const hwAniso = gl.capabilities.getMaxAnisotropy()
    const aniso = Math.min(profile.anisotropy, hwAniso)
    for (const t of list) {
      limitTextureSize(t, profile.maxTextureSize)
      t.colorSpace = THREE.SRGBColorSpace
      t.anisotropy = aniso
      if (profile.lowPower) {
        // Skip mip chain — saves ~33% VRAM on multi-atlas rooms like Arnolfini.
        t.generateMipmaps = false
        t.minFilter = THREE.LinearFilter
        t.magFilter = THREE.LinearFilter
      } else {
        t.generateMipmaps = true
        t.minFilter = THREE.LinearMipmapLinearFilter
      }
    }
  }) as THREE.Texture[]
}
