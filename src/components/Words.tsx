import { Fragment, type CSSProperties } from 'react'

/**
 * Masked word-by-word rise, played when an ancestor gains `.is-visible`.
 * `from` continues the stagger across sibling runs (e.g. into an `<em>`).
 */
export function Words({ text, from = 0 }: { text: string; from?: number }) {
  return (
    <>
      {text.split(' ').map((word, i) => (
        <Fragment key={i}>
          {i > 0 && ' '}
          <span className="w">
            <span style={{ '--wi': from + i } as CSSProperties}>{word}</span>
          </span>
        </Fragment>
      ))}
    </>
  )
}
