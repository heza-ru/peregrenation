import * as THREE from 'three'
import type { BoxCollider } from './walkColliders'

/** [byteOffset, elementCount] into scene.bin (scripts/pipeline/build_arnolfini_world3d.py). */
type Span = [number, number]
type MeshSpans = { position: Span; uv: Span; index: Span }

type Vec3 = [number, number, number]

/** data/paintings/arnolfini-portrait/world3d.json */
export type ArnolfiniWorldData = {
  version: 1
  camera: { f: number; cx: number; cy: number; eyeY: number; eyeZ: number; width: number; height: number; fovPainting: number }
  spawn: { position: Vec3; look: Vec3 }
  eyeHeight: number
  room: BoxCollider & { ceiling: number }
  colliders: BoxCollider[]
  chain: { from: Vec3; to: Vec3 }
  candle: Vec3
  window: { center: Vec3; size: [number, number] }
  anchors: Record<string, Vec3>
}

type SceneIndex = {
  version: 3
  room: (MeshSpans & { page: number })[]
  solids: { page: number; front: MeshSpans; back: MeshSpans }[]
  reliefs: { page: number; front: MeshSpans }[]
  /** objRim: front textures with the silhouette band rebuilt from the body (for side views) */
  pages: { room: string[]; obj: string[]; objBack: string[]; objRim: string[] }
}

export type ArnolfiniScene = {
  pages: SceneIndex['pages']
  room: { page: number; geometry: THREE.BufferGeometry }[]
  solids: { page: number; front: THREE.BufferGeometry; back: THREE.BufferGeometry }[]
  reliefs: { page: number; geometry: THREE.BufferGeometry }[]
}

export function parseArnolfiniWorld(text: string): ArnolfiniWorldData {
  const w = JSON.parse(text) as ArnolfiniWorldData
  if (w.version !== 1 || !w.spawn || !w.room) throw new Error('world3d.json is not an Arnolfini room')
  return w
}

function geometry(bin: ArrayBuffer, spans: MeshSpans, withNormals: boolean): THREE.BufferGeometry {
  const g = new THREE.BufferGeometry()
  g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(bin, spans.position[0], spans.position[1]), 3))
  g.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(bin, spans.uv[0], spans.uv[1]), 2))
  g.setIndex(new THREE.BufferAttribute(new Uint32Array(bin, spans.index[0], spans.index[1]), 1))
  if (withNormals) g.computeVertexNormals()
  g.computeBoundingSphere()
  return g
}

export type ParseArnolfiniSceneOpts = {
  /** Skip normals on low-power devices when using unlit materials (big win on mobile). */
  normals?: boolean
}

export function parseArnolfiniScene(
  indexText: string,
  bin: ArrayBuffer,
  opts: ParseArnolfiniSceneOpts = {},
): ArnolfiniScene {
  const normals = opts.normals !== false
  const index = JSON.parse(indexText) as SceneIndex
  if (index.version !== 3 || !Array.isArray(index.room)) throw new Error('scene.json is not a v3 room scene')
  return {
    pages: index.pages,
    room: index.room.map((m) => ({ page: m.page, geometry: geometry(bin, m, false) })),
    solids: index.solids.map((s) => ({
      page: s.page,
      front: geometry(bin, s.front, normals),
      back: geometry(bin, s.back, normals),
    })),
    reliefs: index.reliefs.map((r) => ({ page: r.page, geometry: geometry(bin, r.front, normals) })),
  }
}

export function disposeArnolfiniScene(scene: ArnolfiniScene): void {
  scene.room.forEach((m) => m.geometry.dispose())
  scene.solids.forEach((s) => {
    s.front.dispose()
    s.back.dispose()
  })
  scene.reliefs.forEach((r) => r.geometry.dispose())
}
