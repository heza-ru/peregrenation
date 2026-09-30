import { Html } from '@react-three/drei'
import { useFrame, useThree } from '@react-three/fiber'
import { useMemo, useRef, useState } from 'react'
import * as THREE from 'three'
import { useWorldStore } from '../app/worldStore'
import type { PaintingFact, SceneEntity, SceneManifest } from '../painting/types'
import { entityWorldPosition } from '../painting/uvPlacement'

type EntityMarkersProps = {
  entities: SceneEntity[]
  facts: PaintingFact[]
  composition: SceneManifest['composition']
  /** Authored 3D hall anchors by entity id (walkable worlds); otherwise markers sit on the fresco plane */
  hallPositions?: Record<string, [number, number, number]>
  /** Pin size relative to the default (a chamber seen from 2–5 m needs smaller pins than a hall) */
  pinScale?: number
}

/** Natural viewing distance for a layered painting plane (matches WorldScene hero camera). */
function viewingDistance(composition: SceneManifest['composition']): number {
  const { planeHeight, cameraFov } = composition
  return (planeHeight / 2) / Math.tan((cameraFov * Math.PI) / 360) * 1.02
}

const _pos = new THREE.Vector3()
const _to = new THREE.Vector3()
const _look = new THREE.Vector3()

export function EntityMarkers({
  entities,
  facts,
  composition,
  hallPositions,
  pinScale = 1,
}: EntityMarkersProps) {
  const hallMode = Boolean(hallPositions)
  const { camera } = useThree()
  const setNearEntity = useWorldStore((s) => s.setNearEntity)
  const markDiscovered = useWorldStore((s) => s.markDiscovered)
  const [nearId, setNearId] = useState<string | null>(null)
  const [awareIds, setAwareIds] = useState<string[]>([])
  const lastNear = useRef<string | null>(null)
  const lastAwareKey = useRef('')

  const factByEntity = useMemo(() => {
    const m = new Map<string, PaintingFact>()
    facts.forEach((f) => {
      if (f.entityId) m.set(f.entityId, f)
    })
    return m
  }, [facts])

  const placed = useMemo(
    () =>
      entities.map((e) => {
        const position: [number, number, number] =
          hallPositions?.[e.id] ?? entityWorldPosition(e, composition)
        return { entity: e, position }
      }),
    [entities, composition, hallPositions],
  )

  const touchPrimary = useWorldStore((s) => s.touchPrimary)
  const viewDist = useMemo(() => viewingDistance(composition), [composition])

  // Halls: short walk-up range. 2D planes: stay active across the natural viewing
  // distance so looking at a figure from the framed start already opens its card.
  const proximity = hallMode
    ? touchPrimary
      ? 4.2
      : 3.2
    : viewDist * (touchPrimary ? 1.2 : 1.08)
  const awareness = hallMode
    ? touchPrimary
      ? 12
      : 10
    : viewDist * 1.4
  /** How centered a figure must be in the look direction before its card opens (2D only). */
  const lookGate = touchPrimary ? 0.78 : 0.85

  useFrame(() => {
    camera.getWorldDirection(_look)
    let best: { id: string; label: string; title: string; teaser: string; score: number } | null =
      null
    const aware: string[] = []
    // On phones, skip distant awareness dots (Html is expensive); only the near card mounts.
    const trackAware = !touchPrimary
    for (const { entity: e, position } of placed) {
      if (!e.interactive) continue
      _pos.set(position[0], position[1], position[2])
      const d = camera.position.distanceTo(_pos)
      if (trackAware && d < awareness) aware.push(e.id)
      if (d >= proximity) continue

      const fact = factByEntity.get(e.id)
      const title = fact?.title ?? e.label
      const raw = fact?.body ?? ''
      const teaser =
        raw.length > 220 ? `${raw.slice(0, raw.lastIndexOf(' ', 220) || 220).trim()}…` : raw

      if (hallMode) {
        const score = -d
        if (!best || score > best.score) {
          best = { id: e.id, label: e.label, title, teaser, score }
        }
      } else {
        _to.copy(_pos).sub(camera.position).normalize()
        const align = _look.dot(_to)
        if (align < lookGate) continue
        const score = align * 4 - d / proximity
        if (!best || score > best.score) {
          best = { id: e.id, label: e.label, title, teaser, score }
        }
      }
    }
    const id = best?.id ?? null
    if (id !== lastNear.current) {
      lastNear.current = id
      setNearId(id)
      setNearEntity(id, best?.label ?? null, best?.title ?? null, best?.teaser ?? null)
      if (id) markDiscovered(id)
    }
    const key = trackAware ? aware.slice().sort().join(',') : ''
    if (key !== lastAwareKey.current) {
      lastAwareKey.current = key
      setAwareIds(trackAware ? aware : [])
    }
  })

  return (
    <group>
      {placed.map(({ entity, position }) => {
        if (!entity.interactive) return null
        const isNear = nearId === entity.id
        const isAware = awareIds.includes(entity.id)
        if (!isNear && !isAware) return null
        const fact = factByEntity.get(entity.id)
        const title = fact?.title ?? entity.label
        const body = fact?.body ?? ''
        return (
          <group key={entity.id} position={position}>
            <Html
              center
              distanceFactor={(isNear ? 7 : 14) * pinScale}
              style={{ pointerEvents: 'none' }}
              zIndexRange={[40, 0]}
            >
              <div
                className={`curiosity-pin${isNear ? ' is-near' : ' is-distant'}`}
              >
                <span className="curiosity-pin__dot" aria-hidden="true" />
                {isNear && (
                  <div className="curiosity-pin__card">
                    <span className="curiosity-pin__eyebrow">{entity.label}</span>
                    <span className="curiosity-pin__title">{title}</span>
                    {body ? (
                      <span className="curiosity-pin__teaser">
                        {body.length > 220
                          ? `${body.slice(0, body.lastIndexOf(' ', 220) || 220).trim()}…`
                          : body}
                      </span>
                    ) : null}
                  </div>
                )}
              </div>
            </Html>
          </group>
        )
      })}
    </group>
  )
}
