import type { PaintingFact, PaintingSources, SceneManifest } from './types'
import { paintingAssetUrl, paintingBaseUrl } from './paths'

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Failed to load ${url}: ${res.status}`)
  return res.json() as Promise<T>
}

export async function loadManifest(paintingId: string): Promise<SceneManifest> {
  return fetchJson(`${paintingBaseUrl(paintingId)}/manifest.json`)
}

export async function loadFacts(paintingId: string): Promise<PaintingFact[]> {
  const data = await fetchJson<{ facts: PaintingFact[] }>(
    `${paintingBaseUrl(paintingId)}/facts.json`,
  )
  return data.facts
}

export async function loadSources(paintingId: string): Promise<PaintingSources> {
  return fetchJson(`${paintingBaseUrl(paintingId)}/sources.json`)
}

export function resolveLayerTexture(manifest: SceneManifest, layer: { texture: string }): string {
  return paintingAssetUrl(manifest.paintingId, layer.texture)
}
