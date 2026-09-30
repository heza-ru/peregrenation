import { useEffect, useId, useLayoutEffect, useRef, useState, type CSSProperties } from 'react'
import { createPortal } from 'react-dom'
import { addFrame, FramePriority } from '../motion/frameLoop'
import { lockScroll } from '../motion/scroll'
import { Pill } from './Pill'

const links = [
  { href: '#build', label: 'How it works' },
  { href: '#learn', label: 'Curiosities' },
  { href: '#gallery', label: 'Gallery' },
  { href: '#export', label: 'Export' },
] as const

type SiteHeaderProps = {
  tone?: 'light' | 'dark'
  onBegin?: () => void
}

export function SiteHeader({ tone = 'light', onBegin }: SiteHeaderProps) {
  const [open, setOpen] = useState(false)
  const [mounted, setMounted] = useState(false)
  const menuId = useId()

  useEffect(() => {
    setMounted(true)
  }, [])

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('keydown', onKey)
    lockScroll(true)
    return () => {
      document.removeEventListener('keydown', onKey)
      lockScroll(false)
    }
  }, [open])

  const close = () => setOpen(false)

  const menu =
    mounted &&
    createPortal(
      <div
        id={menuId}
        className={`mobile-menu${open ? ' is-open' : ''}`}
        inert={!open}
        role="dialog"
        aria-modal="true"
        aria-label="Navigation"
        data-lenis-prevent
      >
        <button type="button" className="menu-toggle is-open mobile-menu__close" aria-label="Close menu" onClick={close}>
          <span className="menu-toggle__bar" />
          <span className="menu-toggle__bar" />
        </button>
        <nav className="mobile-menu__nav">
          {links.map((link, i) => (
            <a key={link.href} href={link.href} onClick={close} style={{ '--i': i } as CSSProperties}>
              {link.label}
            </a>
          ))}
          <div className="mobile-menu__cta" style={{ '--i': links.length } as CSSProperties}>
            <Pill
              href="#enter"
              label="Begin a world"
              tone="accent"
              onClick={(e) => {
                e.preventDefault()
                close()
                onBegin?.()
              }}
            />
          </div>
        </nav>
      </div>,
      document.body,
    )

  return (
    <>
      <header className={`site-header site-header--${tone}`}>
        <nav className="site-nav" aria-label="Primary">
          {links.map((link) => (
            <a key={link.href} href={link.href} className="nav-link">
              <span>{link.label}</span>
            </a>
          ))}
        </nav>

        <button
          type="button"
          className={`menu-toggle${open ? ' is-open' : ''}`}
          aria-label={open ? 'Close menu' : 'Open menu'}
          aria-expanded={open}
          aria-controls={menuId}
          onClick={() => setOpen((v) => !v)}
        >
          <span className="menu-toggle__bar" />
          <span className="menu-toggle__bar" />
        </button>
      </header>
      {menu}
    </>
  )
}

const SECTION_IDS = links.map((l) => l.href.slice(1))

/**
 * Glass nav that docks once the hero is behind you: hides while you read downward,
 * returns the moment you scroll back up, and a pill glides under the current chapter.
 */
export function FloatingNav() {
  const navRef = useRef<HTMLElement>(null)
  const pillRef = useRef<HTMLSpanElement>(null)
  const [active, setActive] = useState<string | null>(null)
  const [hover, setHover] = useState<string | null>(null)

  useEffect(() => {
    const nav = navRef.current
    if (!nav) return
    let lastY = window.scrollY
    let down = 0
    let shown = false
    let current: string | null = null

    let still = 0

    return addFrame((_, dt) => {
      const y = window.scrollY
      const vh = window.innerHeight
      const dy = y - lastY
      lastY = y
      if (dy < -1) down = 0
      else if (dy > 0) down += dy
      still = Math.abs(dy) < 0.5 ? still + dt : 0
      if (still > 1.1) down = 0

      const hero = document.getElementById('top')
      const past = y > (hero ? hero.offsetHeight - vh * 0.8 : vh)
      const atEnd = y + vh >= document.documentElement.scrollHeight - 4
      const next = past && (down < 140 || atEnd)
      if (next !== shown) {
        shown = next
        nav.classList.toggle('is-shown', shown)
      }

      let id: string | null = null
      for (const sid of SECTION_IDS) {
        const el = document.getElementById(sid)
        if (el && el.getBoundingClientRect().top < vh * 0.55) id = sid
      }
      if (id !== current) {
        current = id
        setActive(id)
      }
    }, FramePriority.state)
  }, [])

  useLayoutEffect(() => {
    const nav = navRef.current
    const pill = pillRef.current
    if (!nav || !pill) return
    const target = hover ?? active
    const link = target ? nav.querySelector<HTMLElement>(`a[href="#${target}"]`) : null
    if (!link) {
      pill.style.opacity = '0'
      return
    }
    pill.style.opacity = '1'
    pill.style.width = `${link.offsetWidth}px`
    pill.style.transform = `translate3d(${link.offsetLeft}px, 0, 0)`
  }, [active, hover])

  return (
    <nav ref={navRef} className="float-nav" aria-label="Sections" onPointerLeave={() => setHover(null)}>
      <span ref={pillRef} className="float-nav__pill" aria-hidden="true" />
      {links.map((link) => {
        const id = link.href.slice(1)
        return (
          <a
            key={link.href}
            href={link.href}
            className={active === id ? 'is-active' : undefined}
            aria-current={active === id ? 'true' : undefined}
            onPointerEnter={() => setHover(id)}
            onFocus={() => setHover(id)}
            onBlur={() => setHover(null)}
          >
            {link.label}
          </a>
        )
      })}
    </nav>
  )
}
