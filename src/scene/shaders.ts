export const FULLSCREEN_VERT = /* glsl */ `#version 300 es
out vec2 vUv;
void main() {
  vec2 p = vec2(float((gl_VertexID << 1) & 2), float(gl_VertexID & 2));
  vUv = p;
  gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);
}
`

/**
 * Draws one painting layer the way CSS would: object-fit cover at a focal point inside a
 * box, then translate + scale about a transform origin. Output is premultiplied.
 */
export const LAYER_FRAG = /* glsl */ `#version 300 es
precision highp float;
uniform sampler2D uTex;
uniform vec2 uRes;
uniform vec2 uImg;
uniform vec4 uBox;
uniform vec2 uFocal;
uniform vec2 uOrigin;
uniform vec3 uXform;
uniform float uShadow;
/** Reach: xy = fingertip in texture uv, zw = pull in device px */
uniform vec4 uWarp;
/** Reach falloff radius as a fraction of the rendered layer width; 0 disables */
uniform float uWarpR;
out vec4 outColor;

float coverScale() { return max(uBox.z / uImg.x, uBox.w / uImg.y); }

float reachFalloff(vec2 uv, vec2 rs) {
  float d = length((uv - uWarp.xy) * rs) / (uWarpR * rs.x);
  return 1.0 - smoothstep(0.0, 1.0, d);
}

// Liquify-style pull: the hand travels the full distance, the arm bends back to a still shoulder.
// One fixed-point step evaluates the falloff at the source rather than the destination.
vec2 reach(vec2 uv) {
  if (uWarpR <= 0.0) return uv;
  vec2 rs = uImg * coverScale() * uXform.z;
  vec2 pull = uWarp.zw / rs;
  float f = reachFalloff(uv, rs);
  f = reachFalloff(uv - pull * f, rs);
  return uv - pull * f;
}

vec2 toUv(vec2 s) {
  vec2 local = s - uBox.xy;
  vec2 q = uOrigin + (local - uOrigin - uXform.xy) / uXform.z;
  vec2 rs = uImg * coverScale();
  vec2 off = (uBox.zw - rs) * uFocal;
  return (q - off) / rs;
}

bool inside(vec2 uv) { return all(greaterThanEqual(uv, vec2(0.0))) && all(lessThanEqual(uv, vec2(1.0))); }

float alphaAt(vec2 uv) { return inside(uv) ? texture(uTex, uv).a : 0.0; }

void main() {
  vec2 s = vec2(gl_FragCoord.x, uRes.y - gl_FragCoord.y);
  vec2 uv = reach(toUv(s));
  vec4 c = inside(uv) ? texture(uTex, uv) : vec4(0.0);
  if (uShadow > 0.0) {
    vec2 pxToUv = 1.0 / (uImg * coverScale());
    vec2 base = uv - vec2(0.0, 22.0) * uShadow * pxToUv;
    float a = alphaAt(base);
    for (int i = 0; i < 10; i++) {
      float ang = float(i) * 0.6283;
      vec2 o = vec2(cos(ang), sin(ang)) * 15.0 * uShadow * pxToUv;
      a += alphaAt(base + o) + alphaAt(base + o * 0.45);
    }
    float sa = a / 21.0 * 0.26;
    vec4 sh = vec4(vec3(0.094, 0.055, 0.024) * sa, sa);
    c = c + sh * (1.0 - c.a);
  }
  outColor = c;
}
`

/**
 * Chapter composite. Outgoing scene A turns to luminous line art and burns away behind an
 * ember front into a starfield void; incoming scene B condenses out of overexposed,
 * glittering light behind a second, slower front.
 */
export const COMPOSITE_FRAG = /* glsl */ `#version 300 es
precision highp float;
in vec2 vUv;
out vec4 outColor;
uniform sampler2D uA;
uniform sampler2D uB;
uniform vec2 uRes;
uniform float uP;
uniform float uTime;
uniform float uMode;
uniform vec2 uOrigin;
uniform float uSeed;
uniform float uDimA;
uniform float uDimB;
uniform vec3 uVoid;
uniform float uDpr;
uniform vec2 uPaper;
uniform float uPaperOn;
#define TRAIL 24
/** Cursor tail samples: device px (y up), radius device px, life 0–1; oldest first */
uniform vec4 uTrail[TRAIL];
uniform int uTrailN;
/** Tail bounds in device px (min.xy, max.xy) including the reveal halo */
uniform vec4 uTrailBox;
/** Ring bursts: device px (y up), age in seconds, strength */
uniform vec4 uBurst[4];
uniform int uBurstN;
/** First-visit reveal of scene A out of the void: 0 = void only, 1 = done */
uniform float uIntro;
/** Preloader progress 0–1, gathers light at the origin while uIntro is 0 */
uniform float uLoad;

float hash(vec2 p) {
  p = fract(p * vec2(123.34, 456.21));
  p += dot(p, p + 45.32);
  return fract(p.x * p.y);
}

float noise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x),
             mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
}

float fbm(vec2 p) {
  float v = 0.0;
  float a = 0.5;
  for (int i = 0; i < 5; i++) {
    v += a * noise(p);
    p = p * 2.03 + vec2(17.1, 9.2);
    a *= 0.5;
  }
  return v;
}

float luma(vec3 c) { return dot(c, vec3(0.299, 0.587, 0.114)); }

float sobel(sampler2D t, vec2 uv) {
  vec2 px = 1.25 * uDpr / uRes;
  float a = luma(texture(t, uv + px * vec2(-1.0,  1.0)).rgb);
  float b = luma(texture(t, uv + px * vec2( 0.0,  1.0)).rgb);
  float c = luma(texture(t, uv + px * vec2( 1.0,  1.0)).rgb);
  float d = luma(texture(t, uv + px * vec2(-1.0,  0.0)).rgb);
  float f = luma(texture(t, uv + px * vec2( 1.0,  0.0)).rgb);
  float g = luma(texture(t, uv + px * vec2(-1.0, -1.0)).rgb);
  float h = luma(texture(t, uv + px * vec2( 0.0, -1.0)).rgb);
  float i = luma(texture(t, uv + px * vec2( 1.0, -1.0)).rgb);
  float gx = (c + 2.0 * f + i) - (a + 2.0 * d + g);
  float gy = (a + 2.0 * b + c) - (g + 2.0 * h + i);
  return length(vec2(gx, gy));
}

/** Engraving: the painting sinks to a dark plate, its contours glow warm white */
vec3 sketch(vec3 c, float e) {
  vec3 plate = c * 0.14 + vec3(0.012, 0.014, 0.026);
  float line = smoothstep(0.05, 0.38, e);
  vec3 ink = mix(vec3(1.0, 0.94, 0.84), c * 1.5 + 0.3, 0.3);
  return mix(plate, ink, line);
}

/** Sparse pixel sparkle that re-rolls ~10 times a second */
float glitter(vec2 uv, float density, float salt) {
  vec2 cell = floor(uv * uRes / (1.6 * uDpr));
  float h = hash(cell + floor(uTime * 10.0) * 0.731 + uSeed + salt);
  return step(1.0 - density, h);
}

vec3 starfield(vec2 uv) {
  float asp = uRes.x / uRes.y;
  vec2 p = vec2(uv.x * asp, uv.y);
  vec3 col = vec3(0.004, 0.005, 0.012);
  float neb = fbm(p * 2.1 + uSeed + vec2(0.0, uTime * 0.012));
  float neb2 = fbm(p * 5.3 - uSeed * 0.7);
  col += uVoid * (pow(neb, 2.4) * 1.6 + pow(neb2, 4.0) * 0.6);

  for (int L = 0; L < 2; L++) {
    float sc = L == 0 ? 22.0 : 7.5;
    vec2 g = p * sc + float(L) * 31.7 + uSeed;
    vec2 id = floor(g);
    vec2 f = fract(g) - 0.5;
    float h = hash(id);
    float thr = L == 0 ? 0.62 : 0.8;
    if (h < thr) continue;
    vec2 o = (vec2(hash(id + 1.7), hash(id + 9.1)) - 0.5) * 0.7;
    vec2 dp = (f - o) * (uRes.y / sc) / uDpr;
    float tw = 0.55 + 0.45 * sin(uTime * (1.1 + h * 2.3) + h * 61.0);
    float core = exp(-dot(dp, dp) * (L == 0 ? 1.1 : 0.45));
    float spikes = 0.0;
    if (L == 1) {
      float big = smoothstep(0.9, 0.99, h);
      spikes = (exp(-abs(dp.y) * 1.4 - abs(dp.x) * 0.075) + exp(-abs(dp.x) * 1.4 - abs(dp.y) * 0.075)) * big;
    }
    vec3 tint = mix(vec3(1.0, 0.92, 0.8), vec3(0.8, 0.88, 1.0), hash(id + 3.3));
    col += tint * (core * (L == 0 ? 0.55 : 1.1) + spikes * 0.9) * tw;
  }
  return col;
}

vec3 finish(vec3 c, vec2 uv) {
  float asp = uRes.x / uRes.y;
  float v = smoothstep(1.2, 0.3, length((uv - 0.5) * vec2(asp * 0.75, 1.0)));
  c *= mix(0.8, 1.0, v);
  c += (hash(uv * uRes + fract(uTime * 7.0) * 91.0) - 0.5) * 0.022;
  return c;
}

/**
 * Cream sheet (the gallery) whose top and bottom are held by a live transition front:
 * slowly drifting noise edge, thin ember rim, a sliver of starfield void and sparks.
 */
vec3 paper(vec3 col, vec2 uv) {
  if (uPaperOn < 0.5) return col;
  float asp = uRes.x / uRes.y;
  float px = uRes.y / uDpr;
  float x = uv.x * asp;
  float amp = 26.0 / px;
  float t = uTime;
  float nTop = (fbm(vec2(x * 2.6 + t * 0.045, 3.1 + t * 0.06)) - 0.5) * 2.0
             + (fbm(vec2(x * 13.0 - t * 0.11, 7.7)) - 0.5) * 0.45;
  float nBot = (fbm(vec2(x * 2.6 - t * 0.04, 11.3 - t * 0.05)) - 0.5) * 2.0
             + (fbm(vec2(x * 13.0 + t * 0.1, 19.1)) - 0.5) * 0.45;
  float o = max(uv.y - (uPaper.x + nTop * amp), (uPaper.y + nBot * amp) - uv.y) * px;
  if (o > 140.0) return col;

  vec3 cream = vec3(0.937, 0.902, 0.839) + (hash(floor(uv * uRes / uDpr)) - 0.5) * 0.018;
  cream += vec3(1.0, 0.82, 0.55) * exp(min(o, 0.0) / 7.0) * 0.12;

  float outside = step(0.0, o);
  float catchFire = smoothstep(0.32, 0.72, fbm(vec2(x * 9.0 + t * 0.25, uv.y * 9.0 - t * 0.18)));
  vec3 outer = col * (1.0 - 0.55 * smoothstep(110.0, 18.0, o) * outside);
  outer = mix(outer, starfield(uv), smoothstep(34.0, 6.0, o) * outside * 0.92);
  outer += vec3(1.0, 0.8, 0.52) * glitter(uv, 0.1, 5.1) * smoothstep(44.0, 2.0, o) * outside * (0.45 + catchFire);

  float edge = abs(o);
  vec3 ember = vec3(1.0, 0.42, 0.12) * exp(-edge / 7.0) * 0.5 * (0.35 + 0.65 * catchFire)
             + vec3(1.0, 0.88, 0.64) * exp(-edge / 1.4) * (0.35 + 0.9 * catchFire);

  return mix(outer, cream, smoothstep(0.9, -0.9, o)) + ember;
}

float capsule(vec2 p, vec4 a, vec4 b) {
  vec2 pa = p - a.xy;
  vec2 ba = b.xy - a.xy;
  float h = clamp(dot(pa, ba) / max(dot(ba, ba), 1e-3), 0.0, 1.0);
  return length(pa - ba * h) - mix(a.z, b.z, h);
}

const float BURST_LIFE = 1.5;

/** Signed distance in CSS px to the burnt-through region: cursor tail ∪ expanding burst rings */
float revealField(vec2 sp) {
  float s = 1e4;
  if (uTrailN > 0 && all(greaterThan(sp, uTrailBox.xy)) && all(lessThan(sp, uTrailBox.zw))) {
    s = length(sp - uTrail[uTrailN - 1].xy) - uTrail[uTrailN - 1].z;
    for (int i = 0; i < TRAIL - 1; i++) {
      if (i >= uTrailN - 1) break;
      s = min(s, capsule(sp, uTrail[i], uTrail[i + 1]));
    }
  }
  for (int i = 0; i < 4; i++) {
    if (i >= uBurstN) break;
    vec4 b = uBurst[i];
    float k = clamp(b.z / BURST_LIFE, 0.0, 1.0);
    float R = (1.0 - pow(1.0 - k, 3.0)) * 280.0 * b.w * uDpr;
    float w = mix(52.0, 3.0, sqrt(k)) * uDpr;
    float ring = abs(length(sp - b.xy) - (R - w * 0.5)) - w * 0.5;
    s = min(s, ring + k * k * 46.0 * uDpr);
  }
  return s / uDpr;
}

/**
 * The cursor as a lantern burning through the varnish: the same front as a chapter
 * transition in miniature. Underdrawing ahead of it, char, ember rim, starfield behind.
 */
vec3 lantern(vec3 col, vec2 uv, float onA) {
  if (uTrailN == 0 && uBurstN == 0) return col;
  vec2 sp = uv * uRes;

  vec3 flash = vec3(0.0);
  for (int i = 0; i < 4; i++) {
    if (i >= uBurstN) break;
    vec2 dp = (sp - uBurst[i].xy) / uDpr;
    flash += vec3(1.0, 0.9, 0.72) * exp(-dot(dp, dp) / 2600.0) * smoothstep(0.4, 0.0, uBurst[i].z) * uBurst[i].w * 1.8;
  }

  float s = revealField(sp);
  if (s > 52.0) return col + flash;
  s += (fbm(sp / (uDpr * 40.0) + vec2(uTime * 0.5, -uTime * 0.35) + uSeed) - 0.5) * 13.0;
  if (s > 44.0) return col + flash;

  float catchFire = smoothstep(0.3, 0.72, fbm(sp / (uDpr * 12.0) + vec2(uTime * 0.7, -uTime * 0.45)));
  float edge = onA > 0.5 ? sobel(uA, uv) : sobel(uB, uv);
  vec3 c = mix(col, sketch(col, edge), smoothstep(42.0, 8.0, s));
  c *= 1.0 - 0.55 * smoothstep(12.0, 0.0, s) * step(0.0, s);
  c = mix(c, starfield(uv), smoothstep(0.8, -1.4, s));
  float e = abs(s);
  c += vec3(1.0, 0.42, 0.12) * exp(-e / 6.5) * 0.55 * (0.35 + 0.65 * catchFire);
  c += vec3(1.0, 0.86, 0.62) * exp(-e / 1.4) * (0.3 + 0.9 * catchFire);
  c += vec3(1.0, 0.8, 0.52) * glitter(uv, 0.12, 3.3) * smoothstep(-28.0, 0.0, s) * step(s, 0.0) * (0.5 + catchFire);
  return c + flash;
}

/**
 * First visit, told with the chapter transition's own vocabulary. While loading, a porthole
 * burns open in the void at the origin, its rim the same broken ember front, and scene A
 * glows through it as engraved line art. On release the front races to the corners and A
 * condenses behind it out of overexposed light, as an incoming chapter does.
 */
vec3 intro(vec2 uv) {
  float asp = uRes.x / uRes.y;
  vec2 np = vec2(uv.x * asp, uv.y);
  vec2 far = max(uOrigin, 1.0 - uOrigin) * vec2(asp, 1.0);
  float r = length((uv - uOrigin) * vec2(asp, 1.0));
  float p = uIntro;
  float ease = p * p * (3.0 - 2.0 * p);

  float hole = mix(0.045, 0.19, uLoad) + sin(uTime * 1.3) * 0.003;
  float front = mix(hole, 1.8, pow(ease, 1.2));
  // A small porthole wobbles in proportion to its size; the open front uses the transition's noise
  float n1 = fbm(np * 2.4 + uSeed) - 0.5;
  float n2 = fbm(np * 9.0 - uSeed + vec2(uTime * 0.12, -uTime * 0.08)) - 0.5;
  float big = smoothstep(0.2, 0.7, front);
  float d = r / length(far);
  d = mix(d * (1.0 + n1 * 0.5 + n2 * 0.45), d + n1 * 0.32 + n2 * 0.07, big);
  float t = front - d;

  // Heat haze just around the front
  float heat = exp(-abs(t) * 26.0);
  vec2 haze = vec2(noise(np * 16.0 + vec2(0.0, uTime * 1.6)), noise(np * 16.0 + vec2(7.3, -uTime * 1.3))) - 0.5;
  vec2 wuv = uv + haze * heat * vec2(1.0 / asp, 1.0) * 0.01;

  vec3 A = texture(uA, wuv).rgb;
  float edge = sobel(uA, wuv);
  vec3 lineArt = sketch(A, edge);
  vec3 lit = A * 1.65 + vec3(1.0, 0.96, 0.9) * smoothstep(0.04, 0.5, edge) * 1.1 + 0.05;
  vec3 paint = mix(A, lit, smoothstep(0.38, 0.0, t) * 0.8);
  paint = mix(paint, lineArt + A * 0.45, smoothstep(0.2, 0.0, t) * 0.35);
  vec3 inside = mix(lineArt, paint, smoothstep(0.0, 0.3, p) * smoothstep(0.0, 0.4, t));
  float grain = hash(floor(uv * uRes / (1.25 * uDpr)) + uSeed);
  float aIn = smoothstep(0.0, mix(0.03, 0.16, big), t + (grain - 0.5) * 0.1 * big);

  vec3 col = mix(starfield(uv), inside, aIn);
  col *= 1.0 - 0.5 * smoothstep(0.05, 0.0, t) * step(0.0, t) * (1.0 - big);

  float fade = 1.0 - smoothstep(0.85, 1.0, p);
  float wait = 1.0 - smoothstep(0.0, 0.3, p);
  float catchFire = smoothstep(0.3, 0.72, fbm(np * 11.0 + vec2(uTime * 0.3, -uTime * 0.2) + uSeed));
  float rim = smoothstep(0.022, 0.0, abs(t - 0.004));
  float rimCore = smoothstep(0.0045, 0.0, abs(t));
  float charSide = smoothstep(0.05, 0.0, t) * smoothstep(-0.005, 0.02, t);
  float voidSide = smoothstep(-0.07, 0.0, t) * step(t, 0.0);
  float boost = 1.0 + 0.5 * wait;
  vec3 ember = vec3(1.0, 0.42, 0.12) * (rim * 0.45 + charSide * 0.18) * (0.35 + 0.65 * catchFire);
  ember += vec3(1.0, 0.86, 0.62) * rimCore * (0.25 + 0.9 * catchFire);
  ember += vec3(1.0, 0.8, 0.52) * glitter(uv, 0.1, 0.0) * voidSide * (0.5 + catchFire);
  // Warm bloom the fire throws onto the void around the porthole
  ember += vec3(1.0, 0.5, 0.22) * exp(min(t, 0.0) * 14.0) * step(t, 0.0) * 0.1 * wait;
  col += ember * fade * boost;
  col += vec3(0.88, 0.92, 1.0) * glitter(uv, 0.08, 7.7) * smoothstep(0.05, 0.0, abs(t)) * 0.8 * smoothstep(0.0, 0.05, p);

  // Embers drift toward the porthole while it gathers
  float pull = exp(min(t, 0.0) * 7.0) * step(t, 0.0) * wait;
  col += vec3(1.0, 0.8, 0.52) * glitter(uv, 0.01 + 0.025 * uLoad, 4.4) * pull * 0.5;

  float flash = exp(-r * r * 40.0) * smoothstep(0.0, 0.04, p) * smoothstep(0.24, 0.04, p);
  col += vec3(1.0, 0.92, 0.76) * flash * 2.4;
  return col;
}

void main() {
  vec2 uv = vUv;
  if (uIntro < 1.0) {
    outColor = vec4(finish(intro(uv), uv), 1.0);
    return;
  }
  if (uP <= 0.0) {
    vec3 A = texture(uA, uv).rgb * (1.0 - uDimA);
    outColor = vec4(paper(finish(lantern(A, uv, 1.0), uv), uv), 1.0);
    return;
  }

  float asp = uRes.x / uRes.y;
  float d;
  if (uMode < 0.5) {
    vec2 far = max(uOrigin, 1.0 - uOrigin) * vec2(asp, 1.0);
    d = length((uv - uOrigin) * vec2(asp, 1.0)) / length(far);
  } else if (uMode < 1.5) {
    d = uv.y;
  } else {
    d = ((1.0 - uv.x) * asp + uv.y) / (asp + 1.0);
  }
  vec2 np = vec2(uv.x * asp, uv.y);
  d += (fbm(np * 2.4 + uSeed) - 0.5) * 0.32;
  d += (fbm(np * 9.0 - uSeed + uTime * 0.05) - 0.5) * 0.07;

  float p = uP;
  float burn = mix(-0.45, 1.45, pow(p, 0.85));
  float form = mix(-0.7, 1.75, smoothstep(0.1, 1.0, p));

  // Heat haze: the air right above the front wavers the paint it is about to take
  float toFront = d - burn;
  float heat = exp(-abs(toFront) * 26.0) * smoothstep(0.0, 0.08, p) * (1.0 - smoothstep(0.85, 1.0, p));
  vec2 haze = vec2(noise(np * 16.0 + vec2(0.0, uTime * 1.6)), noise(np * 16.0 + vec2(7.3, -uTime * 1.3))) - 0.5;
  vec2 wuv = uv + haze * heat * vec2(1.0 / asp, 1.0) * 0.012;

  // Outgoing: line art spreading ahead of the fire, charring right before it
  vec3 A = texture(uA, wuv).rgb * (1.0 - uDimA);
  float edgeA = sobel(uA, wuv);
  float sk = smoothstep(0.0, 0.35, p) * (0.4 + 0.6 * smoothstep(0.55, 0.0, toFront));
  vec3 colA = mix(A, sketch(A, edgeA), sk);
  colA *= 1.0 - 0.6 * smoothstep(0.12, 0.0, toFront);

  // Incoming: overexposed, edge-lit light cooling into paint
  vec3 B = texture(uB, wuv).rgb * (1.0 - uDimB);
  float depthB = form - d;
  float edgeB = sobel(uB, wuv);
  float hot = smoothstep(0.38, 0.0, depthB);
  vec3 lit = B * 1.65 + vec3(1.0, 0.96, 0.9) * smoothstep(0.04, 0.5, edgeB) * 1.1 + 0.05;
  vec3 colB = mix(B, lit, hot * 0.8);
  colB = mix(colB, sketch(B, edgeB) + B * 0.45, hot * hot * 0.35);
  // Condensing dust: the scene arrives as a dither that fills in toward the settled side
  float grain = hash(floor(uv * uRes / (1.25 * uDpr)) + uSeed);
  float aB = smoothstep(0.0, 0.16, depthB + (grain - 0.5) * 0.1);

  vec3 col = mix(starfield(uv), colB, aB);
  float aA = smoothstep(-0.012, 0.012, toFront);
  col = mix(col, colA, aA);

  float fade = 1.0 - smoothstep(0.85, 1.0, p);
  // The fire front breaks up: hot where the noise catches, barely smouldering elsewhere
  float catchFire = smoothstep(0.3, 0.72, fbm(np * 11.0 + vec2(uTime * 0.3, -uTime * 0.2) + uSeed));
  float rim = smoothstep(0.022, 0.0, abs(toFront + 0.004));
  float rimCore = smoothstep(0.0045, 0.0, abs(toFront));
  float charSide = smoothstep(0.05, 0.0, toFront) * smoothstep(-0.005, 0.02, toFront);
  float voidSide = smoothstep(-0.07, 0.0, toFront) * step(toFront, 0.0);
  vec3 ember = vec3(1.0, 0.42, 0.12) * (rim * 0.45 + charSide * 0.18) * (0.35 + 0.65 * catchFire);
  ember += vec3(1.0, 0.86, 0.62) * rimCore * (0.25 + 0.9 * catchFire);
  ember += vec3(1.0, 0.8, 0.52) * glitter(uv, 0.1, 0.0) * voidSide * (0.5 + catchFire);
  col += ember * fade;

  float nearForm = smoothstep(0.05, 0.0, abs(depthB));
  col += vec3(0.88, 0.92, 1.0) * glitter(uv, 0.08, 7.7) * nearForm * 0.8;

  if (uMode < 0.5) {
    float r = length((uv - uOrigin) * vec2(asp, 1.0));
    float flash = exp(-r * r * 40.0) * smoothstep(0.0, 0.05, p) * smoothstep(0.26, 0.04, p);
    col += vec3(1.0, 0.92, 0.76) * flash * 2.4;
  }

  outColor = vec4(paper(finish(lantern(col, uv, aA), uv), uv), 1.0);
}
`
