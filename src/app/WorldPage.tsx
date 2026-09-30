import { Canvas } from '@react-three/fiber'
import { Suspense, useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useWorldStore } from './worldStore'
import { loadFacts, loadManifest } from '../painting/loadManifest'
import type { PaintingFact, SceneManifest } from '../painting/types'
import { useTouchPrimary } from '../hooks/useTouchPrimary'
import { nextFrames, whenLandingGlReleased } from '../scene/glHandoff'
import { WorldScene } from '../world/WorldScene'
import { getDeviceProfile } from '../world/deviceProfile'
import { WorldGameHud } from '../ui/world/WorldGameHud'

/**
 * Wait until the landing WebGL context is gone, then a couple of frames,
 * before mounting R3F — otherwise many GPUs show a brown / empty canvas
 * until a full refresh.
 */
function useGlHandoff(): boolean {
  const [ready, setReady] = useState(false)
  useEffect(() => {
    document.documentElement.classList.remove('gl-scene')
    let cancelled = false
    ;(async () => {
      await whenLandingGlReleased()
      await nextFrames(2)
      // Extra beat for Chromium to recycle the compositor surface.
      await new Promise<void>((r) => window.setTimeout(r, 50))
      if (!cancelled) setReady(true)
    })()
    return () => {
      cancelled = true
    }
  }, [])
  return ready
}

export function WorldPage() {
  const { paintingId } = useParams<{ paintingId: string }>()
  const id = paintingId ?? 'school-of-athens'
  const [manifest, setManifest] = useState<SceneManifest | null>(null)
  const [facts, setFacts] = useState<PaintingFact[]>([])
  const [error, setError] = useState<string | null>(null)
  const [sceneReady, setSceneReady] = useState(false)
  const [canvasEpoch, setCanvasEpoch] = useState(0)
  const touchPrimary = useTouchPrimary()
  const setTouchPrimary = useWorldStore((s) => s.setTouchPrimary)
  const profile = useMemo(() => getDeviceProfile(), [])
  const glReady = useGlHandoff()
  const onSceneReady = useCallback(() => setSceneReady(true), [])

  // If textures/GL stall, surface it instead of an endless brown boot screen.
  useEffect(() => {
    if (!manifest || !glReady || sceneReady || error) return
    const t = window.setTimeout(() => {
      setError(
        'This world took too long to open. Check your connection, then try again — or pick another doorway.',
      )
    }, 18000)
    return () => window.clearTimeout(t)
  }, [manifest, glReady, sceneReady, error])

  // Sync touch mode before the canvas mounts ExploreControls (avoids a desktop lock flash on phones).
  useEffect(() => {
    setTouchPrimary(touchPrimary || profile.touchPrimary)
  }, [touchPrimary, profile.touchPrimary, setTouchPrimary])

  useEffect(() => {
    return () => {
      useWorldStore.setState({
        pointerLocked: false,
        exploring: false,
        touchMove: { x: 0, y: 0 },
        nearEntityId: null,
        nearEntityLabel: null,
        nearCuriosityTitle: null,
        nearCuriosityTeaser: null,
        discoveredIds: [],
      })
    }
  }, [])

  useEffect(() => {
    const prev = document.documentElement.style.overflow
    document.documentElement.style.overflow = 'hidden'
    document.body.style.overflow = 'hidden'
    return () => {
      document.documentElement.style.overflow = prev
      document.body.style.overflow = ''
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    setSceneReady(false)
    setError(null)
    setCanvasEpoch(0)
    // Warm the hero still while JSON loads — biggest byte on 2D worlds.
    const preload = document.createElement('link')
    preload.rel = 'preload'
    preload.as = 'image'
    preload.href = `/data/paintings/${id}/painting.jpg`
    document.head.appendChild(preload)
    ;(async () => {
      try {
        const [m, f] = await Promise.all([loadManifest(id), loadFacts(id).catch(() => [])])
        if (!cancelled) {
          setManifest(m)
          setFacts(f)
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load world')
      }
    })()
    return () => {
      cancelled = true
      preload.remove()
    }
  }, [id])

  if (error) {
    return (
      <div className="world-shell world-shell--error">
        <p>{error}</p>
        <Link to="/">Return to doorway</Link>
      </div>
    )
  }

  if (!manifest || !glReady) {
    return (
      <div className="world-shell world-shell--loading game-boot">
        <p className="game-boot__text">Opening the frame…</p>
        <div className="game-boot__bar" />
      </div>
    )
  }

  return (
    <div id="world-root" className="world-shell world-shell--game">
      <WorldGameHud manifest={manifest} entities={manifest.entities} />
      {!sceneReady && (
        <div className="world-boot" aria-live="polite">
          <p className="game-boot__text">
            {profile.lowPower ? 'Loading a lighter chamber…' : 'Opening the frame…'}
          </p>
          <div className="game-boot__bar" />
        </div>
      )}
      <Canvas
        key={`${id}-${canvasEpoch}`}
        shadows={!profile.lowPower}
        dpr={[1, profile.dprMax]}
        frameloop="always"
        gl={{
          antialias: !profile.lowPower,
          powerPreference: profile.lowPower ? 'low-power' : 'high-performance',
          alpha: false,
          stencil: false,
          depth: true,
          failIfMajorPerformanceCaveat: false,
          preserveDrawingBuffer: false,
        }}
        camera={{ fov: 55, near: 0.1, far: 120, position: [0.4, 1.65, 9.5] }}
        style={{ touchAction: 'none' }}
        onCreated={({ gl }) => {
          gl.setClearColor('#1a1612')
          gl.domElement.style.touchAction = 'none'
          if (profile.lowPower) {
            gl.shadowMap.enabled = false
          }
          const canvas = gl.domElement
          const onLost = (e: Event) => {
            e.preventDefault()
            // First loss after doorway handoff: remount once. Refresh used to be the only fix.
            if (canvasEpoch < 1) {
              setSceneReady(false)
              window.setTimeout(() => setCanvasEpoch((n) => n + 1), 120)
              return
            }
            setError(
              'This device ran out of graphics memory. Try closing other tabs, then reopen the world.',
            )
          }
          canvas.addEventListener('webglcontextlost', onLost, false)
        }}
      >
        <Suspense fallback={null}>
          <WorldScene manifest={manifest} facts={facts} onReady={onSceneReady} />
        </Suspense>
      </Canvas>
    </div>
  )
}
