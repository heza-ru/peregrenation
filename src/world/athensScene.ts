import * as THREE from 'three'

/** [byteOffset, elementCount] into scene.bin (scripts/pipeline/build_athens_world3d.py). */
type Span = [number, number]

type MeshSpans = { position: Span; uv: Span; index: Span }

export type AthensSceneIndex = {
  version: number
  arch: (MeshSpans & { page: number })[]
  figures: { page: number; front: MeshSpans; back: MeshSpans }[]
  pages: { arch: string[]; fig: string[]; figBack: string[] }
}

export type AthensScene = {
  index: AthensSceneIndex
  arch: { page: number; geometry: THREE.BufferGeometry }[]
  figures: { page: number; front: THREE.BufferGeometry; back: THREE.BufferGeometry }[]
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

export type ParseAthensSceneOpts = { normals?: boolean }

export function parseAthensScene(
  indexText: string,
  bin: ArrayBuffer,
  opts: ParseAthensSceneOpts = {},
): AthensScene {
  const normals = opts.normals !== false
  const index = JSON.parse(indexText) as AthensSceneIndex
  if (index.version !== 2 || !Array.isArray(index.arch) || !Array.isArray(index.figures)) {
    throw new Error('scene.json is not a v2 Athens scene')
  }
  return {
    index,
    arch: index.arch.map((m) => ({ page: m.page, geometry: geometry(bin, m, false) })),
    figures: index.figures.map((f) => ({
      page: f.page,
      front: geometry(bin, f.front, normals),
      back: geometry(bin, f.back, normals),
    })),
  }
}

export function disposeAthensScene(scene: AthensScene): void {
  scene.arch.forEach((m) => m.geometry.dispose())
  scene.figures.forEach((f) => {
    f.front.dispose()
    f.back.dispose()
  })
}
