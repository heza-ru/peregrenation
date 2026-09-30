import { PointerLockControls } from '@react-three/drei'
import { useFrame, useThree } from '@react-three/fiber'
import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import { useWorldStore } from '../app/worldStore'
import { ATHENS_HALL, athensFloorHeight, resolveAthensPosition } from '../world/athensHallConfig'
import { EXPLORE_LOOK_SPEED, EXPLORE_RUN, EXPLORE_WALK } from './exploreConfig'

const KEYS = {
  KeyW: [0, 1],
  KeyS: [0, -1],
  KeyA: [-1, 0],
  KeyD: [1, 0],
} as const

type KeyName = keyof typeof KEYS

const LOOK_TOUCH = 0.0032
const PITCH_LIMIT = Math.PI / 2 - 0.12

/** How a walkable world keeps the visitor on its floor and out of its solids. */
export type WalkRules = {
  resolve: (p: THREE.Vector3) => void
  /** Eye height for the current spot; `moved` turns true at the visitor's first step. */
  eyeY: (p: THREE.Vector3, moved: boolean) => number
}

const ATHENS_WALK: WalkRules = {
  resolve: (p) => resolveAthensPosition(p),
  eyeY: (p) => athensFloorHeight(p.z) + ATHENS_HALL.eyeHeight,
}

type ExploreControlsProps = {
  enabled: boolean
  /** Floor-clamped walk for School of Athens 3D hall */
  walkMode?: boolean
  /** Floor-clamped walk with a world's own rules (overrides walkMode) */
  walk?: WalkRules
}

export function ExploreControls({ enabled, walkMode = false, walk }: ExploreControlsProps) {
  const { camera, gl } = useThree()
  const rules = walk ?? (walkMode ? ATHENS_WALK : null)
  const moved = useRef(false)
  const held = useRef(new Set<KeyName>())
  const shift = useRef(false)
  const forward = useRef(new THREE.Vector3())
  const right = useRef(new THREE.Vector3())
  const euler = useRef(new THREE.Euler(0, 0, 0, 'YXZ'))
  const lookDrag = useRef<{ id: number; x: number; y: number } | null>(null)
  const touchPrimary = useWorldStore((s) => s.touchPrimary)

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.code === 'ShiftLeft' || e.code === 'ShiftRight') shift.current = true
      if (e.code in KEYS) held.current.add(e.code as KeyName)
    }
    const up = (e: KeyboardEvent) => {
      if (e.code === 'ShiftLeft' || e.code === 'ShiftRight') shift.current = false
      if (e.code in KEYS) held.current.delete(e.code as KeyName)
    }
    window.addEventListener('keydown', down)
    window.addEventListener('keyup', up)
    return () => {
      window.removeEventListener('keydown', down)
      window.removeEventListener('keyup', up)
    }
  }, [])

  useEffect(() => {
    if (!enabled || !touchPrimary) return
    const el = gl.domElement
    euler.current.setFromQuaternion(camera.quaternion)

    const isUi = (t: EventTarget | null) =>
      t instanceof Element && Boolean(t.closest('.mobile-stick, .game-hud__tab, .game-hud__top, a'))

    const onDown = (e: PointerEvent) => {
      if (e.pointerType === 'mouse' && e.button !== 0) return
      if (isUi(e.target)) return
      e.preventDefault()
      lookDrag.current = { id: e.pointerId, x: e.clientX, y: e.clientY }
      useWorldStore.getState().setExploring(true)
      try {
        el.setPointerCapture(e.pointerId)
      } catch {
        /* some WebViews reject capture mid-gesture */
      }
    }
    const onMove = (e: PointerEvent) => {
      const drag = lookDrag.current
      if (!drag || drag.id !== e.pointerId) return
      e.preventDefault()
      const dx = e.clientX - drag.x
      const dy = e.clientY - drag.y
      drag.x = e.clientX
      drag.y = e.clientY
      euler.current.setFromQuaternion(camera.quaternion)
      euler.current.y -= dx * LOOK_TOUCH
      euler.current.x -= dy * LOOK_TOUCH
      euler.current.x = Math.max(-PITCH_LIMIT, Math.min(PITCH_LIMIT, euler.current.x))
      camera.quaternion.setFromEuler(euler.current)
    }
    const onUp = (e: PointerEvent) => {
      if (lookDrag.current?.id === e.pointerId) lookDrag.current = null
    }

    el.addEventListener('pointerdown', onDown, { passive: false })
    el.addEventListener('pointermove', onMove, { passive: false })
    el.addEventListener('pointerup', onUp)
    el.addEventListener('pointercancel', onUp)
    return () => {
      el.removeEventListener('pointerdown', onDown)
      el.removeEventListener('pointermove', onMove)
      el.removeEventListener('pointerup', onUp)
      el.removeEventListener('pointercancel', onUp)
    }
  }, [enabled, touchPrimary, camera, gl])

  useFrame((_, delta) => {
    if (!enabled) return
    const stick = useWorldStore.getState().touchMove
    let mx = stick.x
    let mz = stick.y

    if (held.current.size > 0) {
      let kx = 0
      let kz = 0
      held.current.forEach((k) => {
        kx += KEYS[k][0]
        kz += KEYS[k][1]
      })
      const len = Math.hypot(kx, kz) || 1
      mx = kx / len
      mz = kz / len
    }

    if (Math.abs(mx) > 0.001 || Math.abs(mz) > 0.001) {
      const speed = shift.current ? EXPLORE_RUN : EXPLORE_WALK
      camera.getWorldDirection(forward.current)
      forward.current.y = 0
      forward.current.normalize()
      right.current.crossVectors(forward.current, new THREE.Vector3(0, 1, 0)).normalize()

      const move = speed * delta
      camera.position.addScaledVector(forward.current, mz * move)
      camera.position.addScaledVector(right.current, mx * move)
      moved.current = true
    }

    if (rules) {
      rules.resolve(camera.position)
      const target = rules.eyeY(camera.position, moved.current)
      camera.position.y += (target - camera.position.y) * (1 - Math.exp(-delta * 9))
    }
  })

  if (touchPrimary) return null

  return (
    <PointerLockControls
      selector="#world-root"
      makeDefault
      enabled={enabled}
      pointerSpeed={EXPLORE_LOOK_SPEED}
    />
  )
}
