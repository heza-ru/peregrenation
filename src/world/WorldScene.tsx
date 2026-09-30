import { useFrame, useLoader, useThree } from '@react-three/fiber'
import { Suspense, useEffect, useMemo, useRef, useState } from 'react'
import * as THREE from 'three'
import { ExploreControls, type WalkRules } from '../camera/ExploreControls'
import { paintingAssetUrl } from '../painting/paths'
import type { PaintingFact, SceneManifest } from '../painting/types'
import { ARNOLFINI_VOID, ArnolfiniRoom3D } from './ArnolfiniRoom3D'
import { type ArnolfiniWorldData, disposeArnolfiniScene, parseArnolfiniScene, parseArnolfiniWorld } from './arnolfiniWorld'
import { Architecture } from './Architecture'
import { AthensAtmosphere } from './AthensAtmosphere'
import { AthensFigures } from './AthensFigures'
import { ATHENS_VOID, AthensHall3D } from './AthensHall3D'
import { ATHENS_HALL } from './athensHallConfig'
import { disposeAthensScene, parseAthensScene } from './athensScene'
import { parseAthensWorld } from './athensWorldData'
import { getDeviceProfile } from './deviceProfile'
import { EntityCutouts } from './EntityCutouts'
import { EntityMarkers } from './EntityMarkers'
import { PaintingLayers } from './PaintingLayers'
import { SelectiveAssets } from './SelectiveAssets'
import { resolveWalker } from './walkColliders'
import { assertNotWalkable3DParallax, isWalkable3DWorld } from './worldMode'

type WorldSceneProps = {
  manifest: SceneManifest
  facts: PaintingFact[]
  onReady?: () => void
}

function ReadyPing({ onReady }: { onReady?: () => void }) {
  useEffect(() => {
    onReady?.()
  }, [onReady])
  return null
}

function AthensContent({ manifest, facts, onReady }: WorldSceneProps) {
  const id = manifest.paintingId
  const [raw, sceneIndex] = useLoader(THREE.FileLoader, [
    paintingAssetUrl(id, 'world3d.json'),
    paintingAssetUrl(id, 'scene/scene.json'),
  ])
  const sceneBin = useLoader(THREE.FileLoader, paintingAssetUrl(id, 'scene/scene.bin'), (loader) =>
    loader.setResponseType('arraybuffer'),
  )
  const world = useMemo(() => parseAthensWorld(String(raw)), [raw])
  const scene = useMemo(() => {
    const low = getDeviceProfile().lowPower
    return parseAthensScene(String(sceneIndex), sceneBin as ArrayBuffer, { normals: !low })
  }, [sceneIndex, sceneBin])
  useEffect(() => () => disposeAthensScene(scene), [scene])
  return (
    <>
      <AthensHall3D paintingId={id} scene={scene} />
      <AthensFigures world={world} scene={scene} paintingId={id} />
      {!getDeviceProfile().lowPower ? <AthensAtmosphere world={world} /> : null}
      <EntityMarkers
        entities={manifest.entities}
        facts={facts}
        composition={manifest.composition}
        hallPositions={world.anchors}
      />
      <ReadyPing onReady={onReady} />
    </>
  )
}

/** First-person hall: authored solids + solid figures — never PaintingLayers. */
function AthensWorld(props: WorldSceneProps) {
  const { camera } = useThree()
  const [explore, setExplore] = useState(false)

  useEffect(() => {
    const { spawn, lookAt } = ATHENS_HALL
    camera.position.set(spawn.x, spawn.y, spawn.z)
    camera.lookAt(lookAt.x, lookAt.y, lookAt.z)
    if (camera instanceof THREE.PerspectiveCamera) {
      camera.fov = 62
      camera.near = 0.05
      camera.far = 320
      camera.updateProjectionMatrix()
    }
    const t = window.setTimeout(() => setExplore(true), 350)
    return () => window.clearTimeout(t)
  }, [camera])

  return (
    <>
      <color attach="background" args={[ATHENS_VOID]} />
      <Suspense fallback={null}>
        <AthensContent {...props} />
      </Suspense>
      <ExploreControls enabled={explore} walkMode />
    </>
  )
}

const ARNOLFINI_WALK_RADIUS = 0.2
/** Seconds to rise from the painter's seated eye to standing height after the first step. */
const ARNOLFINI_RISE_S = 1.4

function arnolfiniWalk(world: ArnolfiniWorldData): WalkRules {
  const { room } = world
  const r = ARNOLFINI_WALK_RADIUS
  const bounds = { minX: room.minX + r, maxX: room.maxX - r, minZ: room.minZ + r, maxZ: room.maxZ - r }
  const seated = world.spawn.position[1]
  let risingSince: number | null = null
  return {
    resolve: (p) => resolveWalker(p, [world.colliders], bounds, r),
    eyeY: (_p, moved) => {
      if (!moved) return seated
      risingSince ??= performance.now()
      const t = Math.min(1, (performance.now() - risingSince) / 1000 / ARNOLFINI_RISE_S)
      const ease = t * t * (3 - 2 * t)
      return seated + (world.eyeHeight - seated) * ease
    },
  }
}

function ArnolfiniContent({
  manifest,
  facts,
  onWorld,
  onReady,
}: WorldSceneProps & { onWorld: (w: ArnolfiniWorldData) => void }) {
  const id = manifest.paintingId
  const [raw, sceneIndex] = useLoader(THREE.FileLoader, [
    paintingAssetUrl(id, 'world3d.json'),
    paintingAssetUrl(id, 'scene/scene.json'),
  ])
  const sceneBin = useLoader(THREE.FileLoader, paintingAssetUrl(id, 'scene/scene.bin'), (loader) =>
    loader.setResponseType('arraybuffer'),
  )
  const world = useMemo(() => parseArnolfiniWorld(String(raw)), [raw])
  const scene = useMemo(() => {
    const low = getDeviceProfile().lowPower
    return parseArnolfiniScene(String(sceneIndex), sceneBin as ArrayBuffer, { normals: !low })
  }, [sceneIndex, sceneBin])
  useEffect(() => () => disposeArnolfiniScene(scene), [scene])
  useEffect(() => onWorld(world), [world, onWorld])
  return (
    <>
      <ArnolfiniRoom3D paintingId={id} scene={scene} world={world} />
      <EntityMarkers
        entities={manifest.entities}
        facts={facts}
        composition={manifest.composition}
        hallPositions={world.anchors}
        pinScale={getDeviceProfile().touchPrimary ? 0.28 : 0.22}
      />
      <ReadyPing onReady={onReady} />
    </>
  )
}

/** First-person chamber: starts at the painter's eye (the panel exactly), then walk in. */
function ArnolfiniWorld(props: WorldSceneProps) {
  const { camera } = useThree()
  const [world, setWorld] = useState<ArnolfiniWorldData | null>(null)
  const walk = useMemo(() => (world ? arnolfiniWalk(world) : undefined), [world])

  useEffect(() => {
    if (!world) return
    const [x, y, z] = world.spawn.position
    camera.position.set(x, y, z)
    camera.lookAt(...world.spawn.look)
    if (camera instanceof THREE.PerspectiveCamera) {
      const low = getDeviceProfile().lowPower
      camera.fov = world.camera.fovPainting + 2
      // Mobile GPUs dislike very small near planes; keep depth precision usable.
      camera.near = low ? 0.08 : 0.03
      camera.far = 40
      camera.updateProjectionMatrix()
    }
  }, [camera, world])

  return (
    <>
      <color attach="background" args={[ARNOLFINI_VOID]} />
      <Suspense fallback={null}>
        <ArnolfiniContent {...props} onWorld={setWorld} />
      </Suspense>
      <ExploreControls enabled={Boolean(walk)} walk={walk} />
    </>
  )
}

function LayeredWorld({ manifest, facts, onReady }: WorldSceneProps) {
  // Belt-and-suspenders: never allow Athens (etc.) into parallax mode
  assertNotWalkable3DParallax(manifest.paintingId, 'LayeredWorld')

  const { camera } = useThree()
  // Most curated 2D packs are a single hero plane — no parallax intro to animate.
  // Avoid setState-every-frame (was re-rendering markers/Html ~60×/s).
  const hasDepth = useMemo(
    () =>
      manifest.architecture.length > 0 ||
      manifest.layers.some((l) => l.hero !== true) ||
      manifest.entities.some((e) => Boolean(e.mask)),
    [manifest],
  )
  const [dimensional, setDimensional] = useState(hasDepth ? 0 : 1)
  const [explore, setExplore] = useState(!hasDepth)
  const baseCamera = useRef(new THREE.Vector3())
  const start = useRef(0)
  const lastBucket = useRef(-1)
  const exploreArmed = useRef(!hasDepth)

  const heroPos = useMemo(() => {
    const { planeHeight, cameraFov } = manifest.composition
    const dist = planeHeight / 2 / Math.tan((cameraFov * Math.PI) / 360)
    const y = (0.5 - manifest.composition.horizon) * planeHeight * 0.12
    return new THREE.Vector3(0, y, dist * 1.02)
  }, [manifest])

  useEffect(() => {
    start.current = performance.now()
    lastBucket.current = -1
    camera.position.copy(heroPos)
    camera.lookAt(0, 0, 0)
    baseCamera.current.copy(heroPos)
    if (camera instanceof THREE.PerspectiveCamera) {
      camera.fov = manifest.composition.cameraFov
      camera.near = 0.15
      camera.far = 80
      camera.updateProjectionMatrix()
    }
  }, [camera, heroPos, manifest.composition.cameraFov])

  useEffect(() => {
    if (hasDepth) return
    const t = window.setTimeout(() => {
      if (!exploreArmed.current) {
        exploreArmed.current = true
        setExplore(true)
      }
    }, 220)
    return () => window.clearTimeout(t)
  }, [hasDepth])

  useFrame(() => {
    if (!hasDepth) return
    const t = (performance.now() - start.current) / 1000
    const target = Math.min(1, t / 2.5)
    const bucket = Math.floor(target * 8)
    if (bucket !== lastBucket.current) {
      lastBucket.current = bucket
      setDimensional(target)
    }
    if (target > 0.85 && !exploreArmed.current) {
      exploreArmed.current = true
      setExplore(true)
    }
  })

  const { ambient, directional, directionalIntensity, color } = manifest.lighting
  const lightPos = useMemo(() => {
    return new THREE.Vector3(...directional).normalize().multiplyScalar(10)
  }, [directional])

  return (
    <>
      <ambientLight intensity={ambient} color={color} />
      <directionalLight position={lightPos} intensity={directionalIntensity} color={color} />
      <PaintingLayers manifest={manifest} dimensional={dimensional} baseCamera={baseCamera.current} />
      <Architecture manifest={manifest} dimensional={dimensional} />
      <EntityCutouts manifest={manifest} dimensional={dimensional} />
      <SelectiveAssets manifest={manifest} />
      <EntityMarkers entities={manifest.entities} facts={facts} composition={manifest.composition} />
      <ExploreControls enabled={explore} />
      <ReadyPing onReady={onReady} />
    </>
  )
}

export function WorldScene(props: WorldSceneProps) {
  const id = props.manifest.paintingId
  if (isWalkable3DWorld(id)) {
    switch (id) {
      case 'school-of-athens':
        return <AthensWorld {...props} />
      case 'arnolfini-portrait':
        return <ArnolfiniWorld {...props} />
      default: {
        const unhandled: never = id
        throw new Error(`No 3D room for ${String(unhandled)}`)
      }
    }
  }
  return <LayeredWorld {...props} />
}
