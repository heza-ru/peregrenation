import { COMPOSITE_FRAG, FULLSCREEN_VERT, LAYER_FRAG } from './shaders'

type Rgb = readonly [number, number, number]

export type LayerDraw = {
  src: string
  /** Layer box in CSS px, top-left origin: x, y, w, h */
  box: readonly [number, number, number, number]
  focal: readonly [number, number]
  /** Transform origin inside the box, CSS px */
  origin: readonly [number, number]
  tx: number
  ty: number
  scale: number
  shadow: boolean
  /** Bend the figure's arm so the fingertip (texture uv) travels by `pull` CSS px */
  reach?: { tip: readonly [number, number]; pull: readonly [number, number]; radius: number }
}

export type CompositeParams = {
  progress: number
  time: number
  mode: number
  /** Origin in uv space, y up */
  origin: readonly [number, number]
  seed: number
  dimA: number
  dimB: number
  voidTint: Rgb
  /** Cream sheet top and bottom edges in CSS px from the viewport top, or null when off screen */
  paper: readonly [number, number] | null
  /** Cursor tail, oldest first, CSS px from the top-left */
  trail: readonly TrailPoint[]
  bursts: readonly BurstDraw[]
}

export type TrailPoint = { x: number; y: number; r: number; life: number }
export type BurstDraw = { x: number; y: number; age: number; strength: number }

export const TRAIL_MAX = 24
const BURST_MAX = 4
/** Farthest the reveal reaches beyond a tail capsule, CSS px */
const TRAIL_HALO = 64

type Texture = { tex: WebGLTexture; w: number; h: number }
type Target = { fb: WebGLFramebuffer; tex: WebGLTexture }
type Program = { program: WebGLProgram; uniforms: Map<string, WebGLUniformLocation> }

const MAX_DPR = 1.5

function compile(gl: WebGL2RenderingContext, frag: string): Program {
  const make = (type: number, src: string) => {
    const shader = gl.createShader(type)!
    gl.shaderSource(shader, src)
    gl.compileShader(shader)
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      throw new Error(gl.getShaderInfoLog(shader) ?? 'shader compile failed')
    }
    return shader
  }
  const program = gl.createProgram()!
  gl.attachShader(program, make(gl.VERTEX_SHADER, FULLSCREEN_VERT))
  gl.attachShader(program, make(gl.FRAGMENT_SHADER, frag))
  gl.linkProgram(program)
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    throw new Error(gl.getProgramInfoLog(program) ?? 'program link failed')
  }
  const uniforms = new Map<string, WebGLUniformLocation>()
  const count = gl.getProgramParameter(program, gl.ACTIVE_UNIFORMS) as number
  for (let i = 0; i < count; i++) {
    const info = gl.getActiveUniform(program, i)
    if (!info) continue
    const loc = gl.getUniformLocation(program, info.name)
    if (loc) uniforms.set(info.name, loc)
  }
  return { program, uniforms }
}

export class SceneEngine {
  readonly dpr: number
  private gl: WebGL2RenderingContext
  private layerProg: Program
  private compProg: Program
  private vao: WebGLVertexArrayObject
  private targets: [Target, Target]
  private textures = new Map<string, Texture>()
  private images = new Map<string, Promise<HTMLImageElement>>()
  private width = 1
  private height = 1
  private disposed = false
  private trailBuf = new Float32Array(TRAIL_MAX * 4)
  private burstBuf = new Float32Array(BURST_MAX * 4)

  static create(canvas: HTMLCanvasElement): SceneEngine | null {
    const gl = canvas.getContext('webgl2', {
      alpha: false,
      antialias: false,
      depth: false,
      stencil: false,
      premultipliedAlpha: true,
      powerPreference: 'high-performance',
    })
    if (!gl) return null
    try {
      return new SceneEngine(gl)
    } catch (err) {
      console.warn('[scene] WebGL init failed, using DOM fallback', err)
      return null
    }
  }

  private constructor(gl: WebGL2RenderingContext) {
    this.gl = gl
    this.dpr = Math.min(MAX_DPR, window.devicePixelRatio || 1)
    this.layerProg = compile(gl, LAYER_FRAG)
    this.compProg = compile(gl, COMPOSITE_FRAG)
    this.vao = gl.createVertexArray()!
    this.targets = [this.makeTarget(), this.makeTarget()]
    gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, true)
  }

  private makeTarget(): Target {
    const gl = this.gl
    const tex = gl.createTexture()!
    gl.bindTexture(gl.TEXTURE_2D, tex)
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, null)
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR)
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR)
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE)
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE)
    const fb = gl.createFramebuffer()!
    gl.bindFramebuffer(gl.FRAMEBUFFER, fb)
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0)
    gl.bindFramebuffer(gl.FRAMEBUFFER, null)
    return { fb, tex }
  }

  /** Canvas backing size from its CSS size */
  resize(cssW: number, cssH: number) {
    const w = Math.max(1, Math.round(cssW * this.dpr))
    const h = Math.max(1, Math.round(cssH * this.dpr))
    if (w === this.width && h === this.height) return
    this.width = w
    this.height = h
    const gl = this.gl
    const canvas = gl.canvas as HTMLCanvasElement
    canvas.width = w
    canvas.height = h
    for (const t of this.targets) {
      gl.bindTexture(gl.TEXTURE_2D, t.tex)
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, null)
    }
  }

  load(src: string): Promise<HTMLImageElement> {
    let pending = this.images.get(src)
    if (!pending) {
      const img = new Image()
      img.decoding = 'async'
      img.src = src
      pending = img.decode().then(() => {
        this.upload(src, img)
        return img
      })
      this.images.set(src, pending)
    }
    return pending
  }

  isReady(srcs: readonly string[]) {
    return srcs.every((s) => this.textures.has(s))
  }

  private upload(src: string, img: HTMLImageElement) {
    if (this.disposed) return
    const gl = this.gl
    const tex = gl.createTexture()!
    gl.bindTexture(gl.TEXTURE_2D, tex)
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, gl.RGBA, gl.UNSIGNED_BYTE, img)
    gl.generateMipmap(gl.TEXTURE_2D)
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR)
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR)
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE)
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE)
    this.textures.set(src, { tex, w: img.naturalWidth, h: img.naturalHeight })
  }

  /** Paint a scene's layers into offscreen target 0 (A) or 1 (B) */
  drawScene(slot: 0 | 1, bg: Rgb, layers: readonly LayerDraw[]) {
    const gl = this.gl
    const { program, uniforms: u } = this.layerProg
    gl.bindFramebuffer(gl.FRAMEBUFFER, this.targets[slot].fb)
    gl.viewport(0, 0, this.width, this.height)
    gl.clearColor(bg[0], bg[1], bg[2], 1)
    gl.clear(gl.COLOR_BUFFER_BIT)
    gl.useProgram(program)
    gl.bindVertexArray(this.vao)
    gl.enable(gl.BLEND)
    gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA)
    gl.activeTexture(gl.TEXTURE0)
    gl.uniform1i(u.get('uTex')!, 0)
    gl.uniform2f(u.get('uRes')!, this.width, this.height)

    const k = this.dpr
    for (const layer of layers) {
      const tex = this.textures.get(layer.src)
      if (!tex) continue
      gl.bindTexture(gl.TEXTURE_2D, tex.tex)
      gl.uniform2f(u.get('uImg')!, tex.w, tex.h)
      gl.uniform4f(u.get('uBox')!, layer.box[0] * k, layer.box[1] * k, layer.box[2] * k, layer.box[3] * k)
      gl.uniform2f(u.get('uFocal')!, layer.focal[0], layer.focal[1])
      gl.uniform2f(u.get('uOrigin')!, layer.origin[0] * k, layer.origin[1] * k)
      gl.uniform3f(u.get('uXform')!, layer.tx * k, layer.ty * k, layer.scale)
      gl.uniform1f(u.get('uShadow')!, layer.shadow ? k : 0)
      const r = layer.reach
      gl.uniform4f(u.get('uWarp')!, r?.tip[0] ?? 0, r?.tip[1] ?? 0, (r?.pull[0] ?? 0) * k, (r?.pull[1] ?? 0) * k)
      gl.uniform1f(u.get('uWarpR')!, r ? r.radius : 0)
      gl.drawArrays(gl.TRIANGLES, 0, 3)
    }
    gl.disable(gl.BLEND)
  }

  /** Blend A → B to the screen; progress 0 shows A alone */
  composite(c: CompositeParams) {
    const gl = this.gl
    const { program, uniforms: u } = this.compProg
    gl.bindFramebuffer(gl.FRAMEBUFFER, null)
    gl.viewport(0, 0, this.width, this.height)
    gl.useProgram(program)
    gl.bindVertexArray(this.vao)
    gl.activeTexture(gl.TEXTURE0)
    gl.bindTexture(gl.TEXTURE_2D, this.targets[0].tex)
    gl.uniform1i(u.get('uA')!, 0)
    gl.activeTexture(gl.TEXTURE1)
    gl.bindTexture(gl.TEXTURE_2D, this.targets[1].tex)
    gl.uniform1i(u.get('uB')!, 1)
    gl.uniform2f(u.get('uRes')!, this.width, this.height)
    gl.uniform1f(u.get('uP')!, c.progress)
    gl.uniform1f(u.get('uTime')!, c.time)
    gl.uniform1f(u.get('uMode')!, c.mode)
    gl.uniform2f(u.get('uOrigin')!, c.origin[0], c.origin[1])
    gl.uniform1f(u.get('uSeed')!, c.seed)
    gl.uniform1f(u.get('uDimA')!, c.dimA)
    gl.uniform1f(u.get('uDimB')!, c.dimB)
    gl.uniform3f(u.get('uVoid')!, c.voidTint[0], c.voidTint[1], c.voidTint[2])
    gl.uniform1f(u.get('uDpr')!, this.dpr)
    const cssH = this.height / this.dpr
    gl.uniform1f(u.get('uPaperOn')!, c.paper ? 1 : 0)
    gl.uniform2f(u.get('uPaper')!, c.paper ? 1 - c.paper[0] / cssH : 0, c.paper ? 1 - c.paper[1] / cssH : 0)

    const k = this.dpr
    const trail = c.trail.slice(-TRAIL_MAX)
    let x0 = Infinity
    let y0 = Infinity
    let x1 = -Infinity
    let y1 = -Infinity
    trail.forEach((pt, i) => {
      const x = pt.x * k
      const y = this.height - pt.y * k
      const r = pt.r * k
      this.trailBuf.set([x, y, r, pt.life], i * 4)
      const m = r + TRAIL_HALO * k
      x0 = Math.min(x0, x - m)
      y0 = Math.min(y0, y - m)
      x1 = Math.max(x1, x + m)
      y1 = Math.max(y1, y + m)
    })
    gl.uniform1i(u.get('uTrailN')!, trail.length)
    if (trail.length) {
      gl.uniform4fv(u.get('uTrail[0]')!, this.trailBuf)
      gl.uniform4f(u.get('uTrailBox')!, x0, y0, x1, y1)
    }
    const bursts = c.bursts.slice(-BURST_MAX)
    bursts.forEach((b, i) => this.burstBuf.set([b.x * k, this.height - b.y * k, b.age, b.strength], i * 4))
    gl.uniform1i(u.get('uBurstN')!, bursts.length)
    if (bursts.length) gl.uniform4fv(u.get('uBurst[0]')!, this.burstBuf)

    gl.drawArrays(gl.TRIANGLES, 0, 3)
    gl.activeTexture(gl.TEXTURE0)
  }

  dispose() {
    this.disposed = true
    const gl = this.gl
    for (const t of this.textures.values()) gl.deleteTexture(t.tex)
    for (const t of this.targets) {
      gl.deleteFramebuffer(t.fb)
      gl.deleteTexture(t.tex)
    }
    gl.deleteProgram(this.layerProg.program)
    gl.deleteProgram(this.compProg.program)
    gl.deleteVertexArray(this.vao)
    this.textures.clear()
    this.images.clear()
    // Free the GPU slot so the explore Canvas can create a fresh context
    // without a brown / empty frame after navigating from the landing.
    try {
      gl.getExtension('WEBGL_lose_context')?.loseContext()
    } catch {
      /* ignore */
    }
  }
}
