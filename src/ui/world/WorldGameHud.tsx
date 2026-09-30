import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useWorldStore } from '../../app/worldStore'
import { useTouchPrimary } from '../../hooks/useTouchPrimary'
import type { SceneEntity, SceneManifest } from '../../painting/types'
import { MobileMoveStick } from './MobileMoveStick'
import { isWalkable3DWorld } from '../../world/worldMode'

type WorldGameHudProps = {
  manifest: SceneManifest
  entities: SceneEntity[]
}

export function WorldGameHud({ manifest, entities }: WorldGameHudProps) {
  const touchPrimary = useTouchPrimary()
  const exploring = useWorldStore((s) => s.exploring)
  const pointerLocked = useWorldStore((s) => s.pointerLocked)
  const nearCuriosityTitle = useWorldStore((s) => s.nearCuriosityTitle)
  const discoveredIds = useWorldStore((s) => s.discoveredIds)
  const setTouchPrimary = useWorldStore((s) => s.setTouchPrimary)

  useEffect(() => {
    setTouchPrimary(touchPrimary)
  }, [touchPrimary, setTouchPrimary])

  useEffect(() => {
    const onChange = () => {
      useWorldStore
        .getState()
        .setPointerLocked(document.pointerLockElement === document.getElementById('world-root'))
    }
    document.addEventListener('pointerlockchange', onChange)
    return () => document.removeEventListener('pointerlockchange', onChange)
  }, [])

  const total = entities.filter((e) => e.interactive).length
  const walkable3d = isWalkable3DWorld(manifest.paintingId)
  const active = touchPrimary ? exploring : pointerLocked

  return (
    <div className={`game-hud${touchPrimary ? ' game-hud--touch' : ''}`}>
      <div className="game-hud__frame" />
      <div className="game-hud__vignette" />

      <div className="game-hud__top">
        <Link to="/" className="game-hud__tab">
          Exit
        </Link>
        <div className="game-hud__location">
          <span className="game-hud__chapter">{manifest.painting.artist}</span>
          <span className="game-hud__zone">{manifest.painting.title}</span>
          {walkable3d ? <span className="game-hud__mode">3D hall</span> : null}
        </div>
        <div className="game-hud__stats">
          <span className="game-hud__stat">
            <span className="game-hud__stat-label">Found</span>
            <span className="game-hud__stat-value">
              {discoveredIds.length}/{total}
            </span>
          </span>
        </div>
      </div>

      {!touchPrimary && (
        <div className={`game-hud__crosshair${active ? ' is-live' : ''}`}>
          <span />
          <span />
        </div>
      )}

      {!active && (
        <p className="game-hud__prompt game-hud__prompt--center">
          {touchPrimary
            ? 'Drag to look · stick to walk · look toward a figure'
            : walkable3d
              ? 'Click to enter the hall · WASD to walk the floor'
              : 'Click to wander · look toward a figure to learn'}
        </p>
      )}

      {active && nearCuriosityTitle && (
        <p className="game-hud__near-hint" aria-live="polite">
          {nearCuriosityTitle}
        </p>
      )}

      {touchPrimary ? (
        <MobileMoveStick />
      ) : (
        <>
          <div className="game-hud__modifiers" aria-hidden="true">
            <div className="game-hud__mod">
              <span className="game-hud__keycap game-hud__keycap--wide">Shift</span>
              <span className="game-hud__mod-label">Sprint</span>
            </div>
            <div className="game-hud__mod">
              <span className="game-hud__keycap game-hud__keycap--wide">Esc</span>
              <span className="game-hud__mod-label">Release</span>
            </div>
            <div className="game-hud__mod game-hud__mod--mouse">
              <span className="game-hud__mouse" />
              <span className="game-hud__mod-label">Look</span>
            </div>
          </div>
          <div className="game-hud__wasd" aria-hidden="true">
            <span className="game-hud__keycap game-hud__keycap--w">W</span>
            <span className="game-hud__keycap game-hud__keycap--a">A</span>
            <span className="game-hud__keycap game-hud__keycap--s">S</span>
            <span className="game-hud__keycap game-hud__keycap--d">D</span>
          </div>
        </>
      )}
    </div>
  )
}
