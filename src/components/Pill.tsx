import type { CSSProperties, MouseEvent, PointerEvent } from 'react'

type PillProps = {
  href: string
  label: string
  tone: 'light' | 'accent'
  className?: string
  onClick?: (e: MouseEvent<HTMLAnchorElement>) => void
}

/** Sets the fill's origin to where the pointer crossed the edge, so it floods in and drains out that way. */
function trackEdge(e: PointerEvent<HTMLAnchorElement>) {
  const el = e.currentTarget
  const r = el.getBoundingClientRect()
  el.style.setProperty('--fx', `${(e.clientX - r.left).toFixed(1)}px`)
  el.style.setProperty('--fy', `${(e.clientY - r.top).toFixed(1)}px`)
}

export function Pill({ href, label, tone, className, onClick }: PillProps) {
  const chars = Array.from(label)
  const row = (
    <>
      {chars.map((ch, i) => (
        <span key={i} style={{ '--ci': i } as CSSProperties}>
          {ch === ' ' ? '\u00a0' : ch}
        </span>
      ))}
    </>
  )

  return (
    <a
      href={href}
      className={`pill pill--${tone}${className ? ` ${className}` : ''}`}
      data-magnetic="0.28"
      data-cursor="hide"
      onPointerEnter={trackEdge}
      onPointerLeave={trackEdge}
      onClick={onClick}
    >
      <span className="pill__fill" aria-hidden="true" />
      <span className="pill__label" data-magnetic-inner>
        <span className="sr-only">{label}</span>
        <span className="pill__roll" aria-hidden="true">
          <span className="pill__row">{row}</span>
          <span className="pill__row pill__row--next">{row}</span>
        </span>
      </span>
    </a>
  )
}
