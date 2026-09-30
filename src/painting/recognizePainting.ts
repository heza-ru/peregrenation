import { galleryWorks, type GalleryWork } from '../data'
import type { WorldKind } from '../world/worldMode'
import { worldKindOf } from '../world/worldMode'

export type WorldCatalogEntry = {
  worldId: string
  title: string
  artist: string
  src: string
  kind: WorldKind
  keywords: string[]
}

/** Shipped worlds only — runtime never invents a new world from an upload. */
export function curatedWorlds(kind?: WorldKind | 'all'): WorldCatalogEntry[] {
  return galleryWorks
    .filter((w): w is GalleryWork & { worldId: string } => Boolean(w.worldId))
    .map((w) => ({
      worldId: w.worldId,
      title: w.title,
      artist: w.artist,
      src: w.src,
      kind: worldKindOf(w.worldId),
      keywords: [
        w.id,
        w.worldId,
        w.title,
        w.artist,
        ...w.title.toLowerCase().split(/\s+/),
        ...w.artist.toLowerCase().split(/\s+/),
      ].map((k) => k.toLowerCase()),
    }))
    .filter((w) => !kind || kind === 'all' || w.kind === kind)
}

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.decoding = 'async'
    img.onload = () => resolve(img)
    img.onerror = () => reject(new Error(`Failed to load ${src}`))
    img.src = src
  })
}

/** Persist average-hashes so repeat uploads / retries don’t re-decode 24 thumbs. */
const hashCache = new Map<string, Promise<bigint>>()

/** Compact average hash for cheap similarity (not cryptographic / not Opus). */
function averageHash(src: string, size = 8): Promise<bigint> {
  const cached = hashCache.get(src)
  if (cached) return cached
  const pending = (async () => {
    const img = await loadImage(src)
    const canvas = document.createElement('canvas')
    canvas.width = size
    canvas.height = size
    const ctx = canvas.getContext('2d', { willReadFrequently: true })
    if (!ctx) throw new Error('No 2D context')
    ctx.drawImage(img, 0, 0, size, size)
    const { data } = ctx.getImageData(0, 0, size, size)
    let sum = 0
    const grays: number[] = []
    for (let i = 0; i < data.length; i += 4) {
      const g = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2]
      grays.push(g)
      sum += g
    }
    const avg = sum / grays.length
    let hash = 0n
    grays.forEach((g, i) => {
      if (g >= avg) hash |= 1n << BigInt(i)
    })
    return hash
  })()
  hashCache.set(src, pending)
  pending.catch(() => hashCache.delete(src))
  return pending
}

function hamming(a: bigint, b: bigint): number {
  let x = a ^ b
  let n = 0
  while (x) {
    n += Number(x & 1n)
    x >>= 1n
  }
  return n
}

function matchByFilename(name: string, catalog: WorldCatalogEntry[]): WorldCatalogEntry | null {
  const stem = name.replace(/\.[^.]+$/, '').toLowerCase().replace(/[_-]+/g, ' ')
  let best: WorldCatalogEntry | null = null
  let score = 0
  for (const entry of catalog) {
    let s = 0
    for (const kw of entry.keywords) {
      if (kw.length >= 4 && stem.includes(kw)) s += kw.length
    }
    if (s > score) {
      score = s
      best = entry
    }
  }
  return score >= 8 ? best : null
}

export type RecognizeResult =
  | {
      kind: 'matched'
      worldId: string
      title: string
      artist: string
      confidence: number
      worldKind: WorldKind
    }
  | { kind: 'unmatched'; reason: string }

/**
 * Map an upload/scan onto a shipped curated world.
 * Does not call Opus and does not generate a new scene.
 */
export async function recognizePainting(opts: {
  imageUrl: string
  fileName?: string
  /** Limit recognition to 2D wander or 3D hall worlds. */
  worldKind?: WorldKind | 'all'
}): Promise<RecognizeResult> {
  const filter = opts.worldKind ?? 'all'
  const catalog = curatedWorlds(filter)
  if (!catalog.length) {
    return {
      kind: 'unmatched',
      reason:
        filter === '3d'
          ? 'No 3D halls in that filter — try 2D wander, or pick a doorway below.'
          : filter === '2d'
            ? 'No 2D worlds in that filter — try 3D halls, or pick a doorway below.'
            : 'No curated worlds are shipped yet.',
    }
  }

  if (opts.fileName) {
    const byName = matchByFilename(opts.fileName, catalog)
    if (byName) {
      return {
        kind: 'matched',
        worldId: byName.worldId,
        title: byName.title,
        artist: byName.artist,
        confidence: 0.85,
        worldKind: byName.kind,
      }
    }
  }

  try {
    const probe = await averageHash(opts.imageUrl)
    // Hash the whole catalog in parallel — sequential was ~24 network+decode roundtrips.
    const scored = await Promise.all(
      catalog.map(async (entry) => {
        try {
          const ref = await averageHash(entry.src)
          return { entry, dist: hamming(probe, ref) }
        } catch {
          return null
        }
      }),
    )
    let best: { entry: WorldCatalogEntry; dist: number } | null = null
    for (const row of scored) {
      if (!row) continue
      if (!best || row.dist < best.dist) best = row
    }
    if (best && best.dist <= 12) {
      return {
        kind: 'matched',
        worldId: best.entry.worldId,
        title: best.entry.title,
        artist: best.entry.artist,
        confidence: Math.max(0.5, 1 - best.dist / 24),
        worldKind: best.entry.kind,
      }
    }
  } catch {
    // fall through to unmatched
  }

  const modeHint =
    filter === '3d'
      ? 'Looking in 3D halls only — switch to 2D or All, or pick a masterpiece below.'
      : filter === '2d'
        ? 'Looking in 2D wander worlds only — switch to 3D or All, or pick a masterpiece below.'
        : 'We only open worlds from our curated collection. Pick a masterpiece below — similar scans of those works will be recognized.'

  return {
    kind: 'unmatched',
    reason: modeHint,
  }
}
