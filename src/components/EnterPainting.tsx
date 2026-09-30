import {
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
  type CSSProperties,
  type DragEvent,
  type FormEvent,
} from 'react'
import { createPortal } from 'react-dom'
import { useNavigate } from 'react-router-dom'
import { useSessionStore } from '../app/sessionStore'
import { assets, galleryWorldKind, galleryWorks, type GalleryWork } from '../data'
import { lockScroll } from '../motion/scroll'
import { useTouchPrimary } from '../hooks/useTouchPrimary'
import { recognizePainting } from '../painting/recognizePainting'
import { releaseLandingGl } from '../scene/glHandoff'
import type { WorldKind } from '../world/worldMode'
import { Words } from './Words'

type DropState = 'idle' | 'over' | 'received'
type ModeFilter = 'all' | WorldKind

type EnterPaintingProps = {
  open: boolean
  onClose: () => void
}

const BUILD_STEPS = [
  'Recognizing the masterpiece',
  'Opening the saved world',
  'Anchoring the frame',
  'World ready',
] as const

const MODE_OPTIONS: { id: ModeFilter; label: string; hint: string }[] = [
  { id: 'all', label: 'All', hint: '2D wander + 3D halls' },
  { id: '2d', label: '2D wander', hint: 'Layered painting planes' },
  { id: '3d', label: '3D halls', hint: 'Walkable chambers' },
]

function kindBadge(kind: WorldKind | null): string {
  if (kind === '3d') return '3D hall'
  if (kind === '2d') return '2D wander'
  return 'Soon'
}

function dropLabel(
  state: DropState,
  buildIndex: number,
  unmatched: boolean,
  matchedTitle: string | null,
  touchPrimary: boolean,
  mode: ModeFilter,
): string {
  if (state === 'received') {
    if (unmatched) return 'Not in this collection — choose a masterpiece below'
    if (matchedTitle && buildIndex <= 0) return `Matched · ${matchedTitle}`
    if (buildIndex >= 0 && buildIndex < BUILD_STEPS.length) return BUILD_STEPS[buildIndex]
    return 'Opening the world…'
  }
  const modeBit =
    mode === '3d' ? 'a 3D hall' : mode === '2d' ? 'a 2D world' : 'a curated work'
  switch (state) {
    case 'idle':
      return touchPrimary
        ? `Upload a scan of ${modeBit}, or choose below`
        : `Drop a scan of ${modeBit}, or choose below`
    case 'over':
      return 'Release to recognize the frame'
    default: {
      const never: never = state
      return never
    }
  }
}

const hasFiles = (e: DragEvent) => Array.from(e.dataTransfer.types).includes('Files')

/** Warm world chunk + hero still so Enter → /world feels instant (once per id). */
const warmedWorlds = new Set<string>()
function warmWorld(worldId: string) {
  if (warmedWorlds.has(worldId)) return
  warmedWorlds.add(worldId)
  void import('../app/WorldPage')
  const img = new Image()
  img.decoding = 'async'
  img.src = `/data/paintings/${worldId}/painting.jpg`
}

function WorkRail({
  works,
  pickedId,
  disabled,
  onPick,
}: {
  works: GalleryWork[]
  pickedId: string | null
  disabled: boolean
  onPick: (work: GalleryWork) => void
}) {
  if (!works.length) {
    return <p className="enter-painting__empty">No worlds in this filter — try another mode.</p>
  }
  return (
    <ul className="enter-painting__rail">
      {works.map((work, i) => {
        const kind = galleryWorldKind(work)
        return (
          <li key={work.id} style={{ '--i': i } as CSSProperties}>
            <button
              type="button"
              className={`enter-painting__card${pickedId === work.id ? ' is-active' : ''}${work.worldId ? ' has-world' : ''}`}
              onClick={() => onPick(work)}
              onPointerEnter={() => {
                if (work.worldId) warmWorld(work.worldId)
              }}
              onFocus={() => {
                if (work.worldId) warmWorld(work.worldId)
              }}
              disabled={disabled}
            >
              <img src={work.src} alt="" loading="lazy" decoding="async" />
              <span className={`enter-painting__badge enter-painting__badge--${kind ?? 'soon'}`}>
                {kindBadge(kind)}
              </span>
              <span className="enter-painting__card-meta">
                <span className="enter-painting__card-title">{work.title}</span>
                <span>
                  {work.artist} · {work.year}
                </span>
              </span>
            </button>
          </li>
        )
      })}
    </ul>
  )
}

export function EnterPainting({ open, onClose }: EnterPaintingProps) {
  const navigate = useNavigate()
  const touchPrimary = useTouchPrimary()
  const setPainting = useSessionStore((s) => s.setPainting)
  const setBuildStatus = useSessionStore((s) => s.setBuildStatus)
  const [mounted, setMounted] = useState(false)
  const [visible, setVisible] = useState(false)
  const [state, setState] = useState<DropState>('idle')
  const [buildIndex, setBuildIndex] = useState(-1)
  const [unmatched, setUnmatched] = useState(false)
  const [matchedTitle, setMatchedTitle] = useState<string | null>(null)
  const [pendingWorldId, setPendingWorldId] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [mode, setMode] = useState<ModeFilter>('all')
  const [picked, setPicked] = useState<GalleryWork | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const depth = useRef(0)
  const titleId = useId()
  const closeRef = useRef<HTMLButtonElement>(null)
  const onCloseRef = useRef(onClose)
  onCloseRef.current = onClose

  useEffect(() => {
    setMounted(true)
  }, [])

  useEffect(() => {
    if (!open) return
    const id = requestAnimationFrame(() => setVisible(true))
    lockScroll(true)
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCloseRef.current()
    }
    document.addEventListener('keydown', onKey)
    const focusId = window.setTimeout(() => closeRef.current?.focus(), 80)
    return () => {
      cancelAnimationFrame(id)
      window.clearTimeout(focusId)
      document.removeEventListener('keydown', onKey)
      lockScroll(false)
    }
  }, [open])

  useEffect(() => {
    if (state !== 'received') return
    if (unmatched || !pendingWorldId) {
      setBuildStatus('error', 'No matching curated world')
      const id = window.setTimeout(() => {
        setState('idle')
        setUnmatched(false)
        setBuildIndex(-1)
        setMatchedTitle(null)
      }, 3600)
      return () => window.clearTimeout(id)
    }

    setBuildStatus('processing')
    let step = 0
    setBuildIndex(0)
    let navigateTimer = 0
    // Capture now — closing the modal must not wipe pendingWorldId mid-flight.
    const worldId = pendingWorldId
    const interval = window.setInterval(() => {
      step += 1
      if (step < BUILD_STEPS.length) {
        setBuildIndex(step)
        return
      }
      window.clearInterval(interval)
      setBuildStatus('ready', BUILD_STEPS[BUILD_STEPS.length - 1])
      setPainting(worldId, preview)
      // Free doorway WebGL *before* R3F mounts — same-tab nav otherwise leaves a
      // dead/brown world Canvas until a full refresh.
      navigateTimer = window.setTimeout(() => {
        void releaseLandingGl().then(() => {
          navigate(`/world/${worldId}`)
        })
      }, 40)
    }, 550)

    return () => {
      window.clearInterval(interval)
      window.clearTimeout(navigateTimer)
    }
  }, [state, unmatched, pendingWorldId, preview, navigate, setPainting, setBuildStatus])

  useEffect(() => {
    if (open) return
    // Don't tear down mid-handoff if a world route is already loading.
    if (window.location.pathname.startsWith('/world/')) return
    setState('idle')
    setQuery('')
    setPicked(null)
    setBuildIndex(-1)
    setUnmatched(false)
    setMatchedTitle(null)
    setPendingWorldId(null)
    setPreview((prev) => {
      if (prev?.startsWith('blob:')) URL.revokeObjectURL(prev)
      return null
    })
    depth.current = 0
  }, [open])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return galleryWorks.filter((w) => {
      const kind = galleryWorldKind(w)
      if (mode !== 'all' && kind !== mode) return false
      if (!q) return true
      return (
        w.title.toLowerCase().includes(q) ||
        w.artist.toLowerCase().includes(q) ||
        w.year.toLowerCase().includes(q)
      )
    })
  }, [query, mode])

  const halls = useMemo(() => filtered.filter((w) => galleryWorldKind(w) === '3d'), [filtered])
  const wander = useMemo(() => filtered.filter((w) => galleryWorldKind(w) === '2d'), [filtered])

  const backdrop = preview ?? picked?.src ?? assets.littaMadonna

  const openWorld = (worldId: string, src?: string, title?: string) => {
    if (src) {
      setPreview((prev) => {
        if (prev?.startsWith('blob:') && prev !== src) URL.revokeObjectURL(prev)
        return src
      })
    }
    setUnmatched(false)
    setMatchedTitle(title ?? null)
    setPendingWorldId(worldId)
    setState('received')
  }

  const receiveUpload = async (file: File) => {
    const url = URL.createObjectURL(file)
    setPicked(null)
    setPreview((prev) => {
      if (prev?.startsWith('blob:') && prev !== url) URL.revokeObjectURL(prev)
      return url
    })
    setUnmatched(false)
    setMatchedTitle(null)
    setPendingWorldId(null)
    setBuildIndex(0)
    setState('received')
    setBuildStatus('processing', 'Recognizing…')

    const result = await recognizePainting({
      imageUrl: url,
      fileName: file.name,
      worldKind: mode,
    })
    if (result.kind === 'matched') {
      setMatchedTitle(result.title)
      setPendingWorldId(result.worldId)
      setUnmatched(false)
      return
    }
    setUnmatched(true)
    setPendingWorldId(null)
    setBuildStatus('error', result.reason)
  }

  const onDragEnter = (e: DragEvent<HTMLDivElement>) => {
    if (!hasFiles(e)) return
    e.preventDefault()
    depth.current += 1
    setState('over')
  }
  const onDragOver = (e: DragEvent<HTMLDivElement>) => {
    if (hasFiles(e)) e.preventDefault()
  }
  const onDragLeave = () => {
    depth.current = Math.max(0, depth.current - 1)
    if (depth.current === 0) setState((s) => (s === 'over' ? 'idle' : s))
  }
  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    if (!hasFiles(e)) return
    e.preventDefault()
    depth.current = 0
    const file = e.dataTransfer.files?.[0]
    if (file?.type.startsWith('image/')) {
      void receiveUpload(file)
      return
    }
    setUnmatched(true)
    setState('received')
  }
  const onPickFile = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    void receiveUpload(file)
  }
  const onPickWork = (work: GalleryWork) => {
    setPicked(work)
    setPreview(work.src)
    setQuery(work.title)
    if (work.worldId) {
      openWorld(work.worldId, work.src, work.title)
      return
    }
    setUnmatched(true)
    setPendingWorldId(null)
    setMatchedTitle(null)
    setState('received')
    setBuildStatus('error', 'This masterpiece is not a shipped world yet')
  }
  const onSearch = (e: FormEvent) => {
    e.preventDefault()
    const first = filtered[0]
    if (first) onPickWork(first)
  }

  if (!mounted || (!open && !visible)) return null

  const label = dropLabel(state, buildIndex, unmatched, matchedTitle, touchPrimary, mode)
  const showSteps = state === 'received' && pendingWorldId && !unmatched
  const busy = state === 'received' && !unmatched

  return createPortal(
    <div
      className={`enter-painting${visible && open ? ' is-open is-visible' : ''}${state === 'received' ? ' is-reading' : ''}`}
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      data-lenis-prevent
      inert={!open}
      onTransitionEnd={(e) => {
        if (e.target === e.currentTarget && !open) setVisible(false)
      }}
    >
      <div className="enter-painting__scene" aria-hidden="true">
        <img key={backdrop} src={backdrop} alt="" className="enter-painting__bg" />
        <div className="enter-painting__veil" />
        <div className="enter-painting__grain" />
      </div>

      <button
        ref={closeRef}
        type="button"
        className="enter-painting__close"
        aria-label="Close"
        onClick={onClose}
      >
        <span />
        <span />
      </button>

      <div className="enter-painting__body">
        <header className="enter-painting__intro">
          <span className="eyebrow">Add a painting</span>
          <h2 id={titleId}>
            <Words text="Bring your" /> <em><Words text="favourite masterpiece." from={2} /></em>
          </h2>
          <p>
            Choose <strong>2D wander</strong> or a <strong>3D hall</strong>, then drop a scan or pick
            a doorway. We only open worlds from this curated set.
          </p>
        </header>

        <div
          className="enter-painting__modes"
          role="radiogroup"
          aria-label="World type"
        >
          {MODE_OPTIONS.map((opt) => (
            <button
              key={opt.id}
              type="button"
              role="radio"
              aria-checked={mode === opt.id}
              className={`enter-painting__mode${mode === opt.id ? ' is-active' : ''}`}
              onClick={() => setMode(opt.id)}
              disabled={busy}
              title={opt.hint}
            >
              <span className="enter-painting__mode-label">{opt.label}</span>
              <span className="enter-painting__mode-hint">{opt.hint}</span>
            </button>
          ))}
        </div>

        <div
          className={`enter-painting__tray enter-painting__tray--${state}`}
          onDragEnter={onDragEnter}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
        >
          <label className="enter-painting__zone" data-cursor="Upload">
            <input type="file" accept="image/*" className="sr-only" onChange={onPickFile} />
            <svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
              <path d="M11 15 V3 M6 8 L11 3 L16 8 M3 15 V19 H19 V15" />
            </svg>
            <span key={`${state}-${buildIndex}-${unmatched}-${matchedTitle}-${mode}`}>{label}</span>
          </label>

          {showSteps && (
            <div className="enter-painting__steps" aria-live="polite">
              {BUILD_STEPS.map((step, i) => (
                <span
                  key={step}
                  className={`enter-painting__step${i < buildIndex ? ' is-done' : ''}${i === buildIndex ? ' is-active' : ''}`}
                >
                  {step}
                </span>
              ))}
            </div>
          )}

          <form className="enter-painting__search" onSubmit={onSearch}>
            <label className="sr-only" htmlFor="enter-painting-search">
              Search by title or artist
            </label>
            <input
              id="enter-painting-search"
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by title or artist"
              autoComplete="off"
              disabled={busy}
            />
            <button type="submit" disabled={!filtered.length || busy}>
              Open
            </button>
          </form>
        </div>

        <div className="enter-painting__gallery">
          {mode === 'all' ? (
            <>
              <div className="enter-painting__group">
                <span className="mono-label">3D halls · walkable chambers</span>
                <WorkRail works={halls} pickedId={picked?.id ?? null} disabled={busy} onPick={onPickWork} />
              </div>
              <div className="enter-painting__group">
                <span className="mono-label">2D wander · layered painting planes</span>
                <WorkRail works={wander} pickedId={picked?.id ?? null} disabled={busy} onPick={onPickWork} />
              </div>
            </>
          ) : (
            <div className="enter-painting__group">
              <span className="mono-label">
                {mode === '3d' ? '3D halls · walkable chambers' : '2D wander · layered painting planes'}
              </span>
              <WorkRail works={filtered} pickedId={picked?.id ?? null} disabled={busy} onPick={onPickWork} />
            </div>
          )}
        </div>
      </div>
    </div>,
    document.body,
  )
}
