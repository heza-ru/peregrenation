export type Evidence = 'observed' | 'strongly_inferred' | 'weakly_inferred'

export type SceneLayer = {
  id: string
  label: string
  depthBand: number
  texture: string
  z: number
  parallax: number
  opacity: number
  hero?: boolean
  mask?: string
}

export type SceneEntity = {
  id: string
  type: string
  label: string
  position: [number, number, number]
  /** Painting UV (0–1, origin top-left). Preferred placement for markers / cutouts. */
  promptPoint?: [number, number]
  scale: [number, number, number]
  depth: number
  importance: number
  interactive: boolean
  confidence: number
  evidence: Evidence
  mask?: string
  /** Optional cutout quad size in world units (defaults derived from plane). */
  cutoutWidth?: number
  cutoutHeight?: number
}

export type ArchPrimitive = {
  id: string
  type: 'plane' | 'cylinder' | 'box'
  position: [number, number, number]
  rotation?: [number, number, number]
  size?: [number, number] | [number, number, number]
  radius?: number
  height?: number
  opacity?: number
}

/** Selective GLB props — never a full-painting mesh. Empty until authored. */
export type SceneAsset = {
  id: string
  url: string
  position: [number, number, number]
  rotation?: [number, number, number]
  scale?: [number, number, number]
}

export type SceneManifest = {
  schemaVersion: number
  paintingId: string
  pipelineVersion: string
  sceneAnalysisVersion: string
  segmentationVersion: string
  depthVersion: string
  painting: {
    title: string
    artist: string
    date: string
    medium: string
    source: string
  }
  composition: {
    aspectRatio: number
    horizon: number
    vanishingPoint: [number, number]
    cameraFov: number
    planeWidth: number
    planeHeight: number
  }
  layers: SceneLayer[]
  entities: SceneEntity[]
  architecture: ArchPrimitive[]
  /** Optional selective meshes; omit or [] for cutout-only worlds. */
  assets?: SceneAsset[]
  lighting: {
    ambient: number
    directional: [number, number, number]
    directionalIntensity: number
    color: string
  }
  palette: string[]
}

export type FactConfidence = 'documented' | 'scholarly_interpretation' | 'ai_inference'

export type PaintingFact = {
  id: string
  entityId?: string
  title: string
  body: string
  category: string
  confidence: FactConfidence
  sources: string[]
}

export type PaintingSources = {
  paintingId: string
  image: {
    file: string
    sourceUrl: string
    retrievalUrl: string
    license: string
    credit: string
    retrievedAt: string
  }
  references: { id: string; title: string; publisher: string; url: string }[]
}
