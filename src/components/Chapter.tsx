import type { CSSProperties, ReactNode } from 'react'
import type { SceneId, Variant } from '../scene/scenes'

type ChapterProps = {
  id: string
  scene: SceneId
  variant: Variant
  title: string
  kicker: ReactNode
  children: ReactNode
}

/**
 * A chapter owns a painted scene on the fixed canvas. Its stage is a pinned title card
 * that rises out of the transition (driven by `--in`), then the content scrolls over it.
 */
export function Chapter({ id, scene, variant, title, kicker, children }: ChapterProps) {
  return (
    <section id={id} className={`chapter chapter--${variant}`} data-scene={scene} data-variant={variant}>
      <div className="chapter__stage">
        <div className="chapter__pin">
          <div className="chapter__heading">
            <h2 className="chapter__title" aria-label={title}>
              {Array.from(title).map((ch, i) => (
                <span key={i} aria-hidden="true" data-ch={ch} style={{ '--i': i } as CSSProperties}>
                  {ch}
                </span>
              ))}
            </h2>
            <p className="chapter__kicker">{kicker}</p>
          </div>
        </div>
      </div>
      <div className="chapter__body">{children}</div>
    </section>
  )
}

/**
 * Cream sheet (the gallery). With WebGL on, the scene canvas paints the sheet and its live
 * transition-front edges behind this element; without it the sheet falls back to CSS cream.
 */
export function PaperSection({ id, children }: { id: string; children: ReactNode }) {
  return (
    <div id={id} className="paper" data-paper>
      {children}
    </div>
  )
}
