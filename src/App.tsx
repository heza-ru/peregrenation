import { useEffect, useState } from 'react'
import { Chapter, PaperSection } from './components/Chapter'
import { Cursor } from './components/Cursor'
import { EnterPainting } from './components/EnterPainting'
import { ScrollProgress } from './components/MotionChrome'
import { Hero } from './components/Hero'
import { SceneCanvas } from './components/SceneCanvas'
import {
  BuildSection,
  CtaFooter,
  ExportSection,
  GallerySection,
  LearnSection,
} from './components/Sections'
import { FloatingNav } from './components/SiteHeader'
import { useLenis } from './hooks/useLenis'
import {
  usePrefersReducedMotion,
  useRevealSystem,
  useSmoothAnchors,
} from './hooks/useMotion'
import { UnderdrawingFilter } from './components/UnderdrawingFilter'
import { useGilt } from './motion/gilt'
import { useInteractions } from './motion/interactions'
import './index.css'
import 'lenis/dist/lenis.css'

/** Defer the full-page WebGL backdrop until after first paint / idle — big LCP win on mobile. */
function useDeferredScene(enabled: boolean): boolean {
  const [ready, setReady] = useState(false)
  useEffect(() => {
    if (!enabled) return
    let cancelled = false
    const arm = () => {
      if (!cancelled) setReady(true)
    }
    if (typeof window.requestIdleCallback === 'function') {
      const id = window.requestIdleCallback(arm, { timeout: 1800 })
      return () => {
        cancelled = true
        window.cancelIdleCallback(id)
      }
    }
    const t = globalThis.setTimeout(arm, 400)
    return () => {
      cancelled = true
      globalThis.clearTimeout(t)
    }
  }, [enabled])
  return ready
}

export default function App() {
  const reduced = usePrefersReducedMotion()
  const [enterOpen, setEnterOpen] = useState(false)
  const sceneReady = useDeferredScene(!reduced)
  useLenis(reduced)
  useRevealSystem()
  useSmoothAnchors(reduced)
  useInteractions(reduced)
  useGilt(reduced)

  return (
    <>
      <UnderdrawingFilter />
      {sceneReady ? <SceneCanvas reduced={reduced} /> : null}
      <div className={`page${reduced ? ' reduce-motion' : ''}`}>
        <ScrollProgress />
        <FloatingNav />
        <Hero onBegin={() => setEnterOpen(true)} />
        <Chapter
          id="build"
          scene="build"
          variant="ignite"
          title="Build"
          kicker={
            <>
              Every painting is a doorway <em>into its painter’s mind.</em>
            </>
          }
        >
          <BuildSection />
        </Chapter>
        <Chapter
          id="learn"
          scene="learn"
          variant="rise"
          title="Wander"
          kicker={
            <>
              Step through, and learn <em>what they hid there.</em>
            </>
          }
        >
          <LearnSection />
        </Chapter>
        <PaperSection id="gallery">
          <GallerySection />
        </PaperSection>
        <Chapter
          id="export"
          scene="export"
          variant="paper"
          title="Export"
          kicker={
            <>
              Carry every curiosity <em>out of the frame.</em>
            </>
          }
        >
          <ExportSection />
        </Chapter>
        <Chapter
          id="begin"
          scene="begin"
          variant="diagonal"
          title="Begin"
          kicker={
            <>
              The frame is only <em>the beginning.</em>
            </>
          }
        >
          <CtaFooter onBegin={() => setEnterOpen(true)} />
        </Chapter>
      </div>
      <EnterPainting open={enterOpen} onClose={() => setEnterOpen(false)} />
      <Cursor reduced={reduced} />
    </>
  )
}
