/**
 * Doorway WebGL (SceneEngine) and explore WebGL (R3F) cannot share a healthy GPU
 * slot on many browsers. Release the landing context *before* opening /world,
 * and wait for that release before mounting the R3F Canvas.
 */

type Teardown = () => Promise<void>

let teardown: Teardown | null = null
/** Resolves when no landing WebGL is holding a context (or never was). */
let gate: Promise<void> = Promise.resolve()
let openGate: (() => void) | null = null

/** SceneCanvas registers its disposer while the landing backdrop is live. */
export function registerLandingGl(dispose: Teardown): () => void {
  // Close the gate until this backdrop is fully released.
  gate = new Promise<void>((resolve) => {
    openGate = resolve
  })

  const run = async () => {
    try {
      await dispose()
    } finally {
      openGate?.()
      openGate = null
    }
  }

  teardown = run

  return () => {
    if (teardown === run) teardown = null
  }
}

/** Drop the landing WebGL context (no-op if already gone / never created). */
export function releaseLandingGl(): Promise<void> {
  const fn = teardown
  teardown = null
  if (fn) void fn()
  return gate
}

/** WorldPage waits here so it never opens a second context mid-teardown. */
export function whenLandingGlReleased(): Promise<void> {
  return gate
}

/** Force-lose + wait for the event so the GPU slot is actually free. */
export function loseWebGlContext(canvas: HTMLCanvasElement, gl: WebGLRenderingContext): Promise<void> {
  return new Promise((resolve) => {
    let settled = false
    const finish = () => {
      if (settled) return
      settled = true
      canvas.removeEventListener('webglcontextlost', onLost)
      window.clearTimeout(safety)
      resolve()
    }
    const onLost = (e: Event) => {
      e.preventDefault()
      finish()
    }
    canvas.addEventListener('webglcontextlost', onLost, false)
    const safety = window.setTimeout(finish, 200)
    try {
      const ext = gl.getExtension('WEBGL_lose_context') as { loseContext: () => void } | null
      if (ext) ext.loseContext()
      else finish()
    } catch {
      finish()
    }
  })
}

export function nextFrames(n = 2): Promise<void> {
  return new Promise((resolve) => {
    const step = (left: number) => {
      if (left <= 0) {
        resolve()
        return
      }
      requestAnimationFrame(() => step(left - 1))
    }
    step(n)
  })
}
