import { useEffect, useRef } from 'react'
import { ACCENT } from '../data'
import { addFrame, FramePriority } from '../motion/frameLoop'

export function ScrollProgress() {
  const barRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const bar = barRef.current
    if (!bar) return
    let last = -1
    return addFrame(() => {
      const max = document.documentElement.scrollHeight - window.innerHeight
      const p = max > 0 ? Math.min(1, Math.max(0, window.scrollY / max)) : 0
      if (Math.abs(p - last) < 1e-4) return
      last = p
      bar.style.transform = `scaleX(${p.toFixed(4)})`
    }, FramePriority.state)
  }, [])

  return (
    <div className="scroll-progress" aria-hidden="true">
      <div ref={barRef} className="scroll-progress__bar" />
    </div>
  )
}

/** Renaissance drafting grid — golden ratio + diagonals (Shopify Editions-inspired) */
export function CompositionGrid({ tone = 'light' }: { tone?: 'light' | 'dark' }) {
  const stroke = tone === 'light' ? 'rgba(42,30,20,0.12)' : 'rgba(201,162,74,0.14)'
  const accent = tone === 'light' ? 'rgba(122,58,34,0.18)' : 'rgba(224,98,58,0.22)'

  return (
    <svg className="comp-grid" viewBox="0 0 1440 900" preserveAspectRatio="none" aria-hidden="true">
      <defs>
        <pattern id="pg-dash" width="12" height="12" patternUnits="userSpaceOnUse">
          <path d="M0 0 H6" stroke={stroke} strokeWidth="0.6" />
        </pattern>
      </defs>
      {/* thirds */}
      <path d="M480 0 V900 M960 0 V900 M0 300 H1440 M0 600 H1440" stroke={stroke} strokeWidth="0.7" fill="none" />
      {/* golden ratio verticals ~0.382 / 0.618 */}
      <path d="M550 0 V900 M890 0 V900" stroke={accent} strokeWidth="0.8" strokeDasharray="4 6" fill="none" />
      <path d="M0 344 H1440 M0 556 H1440" stroke={accent} strokeWidth="0.8" strokeDasharray="4 6" fill="none" />
      {/* diagonals */}
      <path d="M0 0 L1440 900 M1440 0 L0 900" stroke={stroke} strokeWidth="0.55" fill="none" />
      {/* center frame */}
      <rect x="120" y="80" width="1200" height="740" fill="none" stroke={stroke} strokeWidth="0.7" />
    </svg>
  )
}

/** Intensity comes from the `--spark` custom property (0–1) set by the hero motion loop. */
export function SparkField() {
  const sparks = [
    { x: '48%', y: '52%', d: 2.2, delay: '0s' },
    { x: '51%', y: '49%', d: 1.6, delay: '0.4s' },
    { x: '46%', y: '55%', d: 1.4, delay: '0.9s' },
    { x: '53%', y: '54%', d: 1.8, delay: '1.3s' },
    { x: '49%', y: '47%', d: 1.2, delay: '1.8s' },
    { x: '55%', y: '50%', d: 1.5, delay: '2.2s' },
    { x: '44%', y: '50%', d: 1.3, delay: '2.7s' },
  ]

  return (
    <div className="spark-field" aria-hidden="true">
      {sparks.map((s, i) => (
        <span
          key={i}
          className="spark-field__dot"
          style={{
            left: s.x,
            top: s.y,
            width: s.d,
            height: s.d,
            animationDelay: s.delay,
            background: i % 2 === 0 ? ACCENT : '#C9A24A',
          }}
        />
      ))}
    </div>
  )
}
