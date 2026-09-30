import { useFrame } from '@react-three/fiber'
import { useEffect, useMemo, useRef } from 'react'
import * as THREE from 'three'
import type { ArnolfiniScene, ArnolfiniWorldData } from './arnolfiniWorld'
import { getDeviceProfile } from './deviceProfile'
import { useSceneTextures } from './sceneTextures'

/** Daylight from the window on the left, slightly in front of the couple, as van Eyck lit them. */
const LIGHT = new THREE.Vector3(-0.62, 0.42, 0.66).normalize()

export const ARNOLFINI_VOID = '#0d0a07'

function roomMaterial(map: THREE.Texture): THREE.MeshBasicMaterial {
  return new THREE.MeshBasicMaterial({ map, side: THREE.DoubleSide, toneMapped: false })
}

/**
 * Painted value where a surface faces the painter; turning towards / away from the window
 * lightens / shades it. `rimMap` (same layout) has the silhouette band rebuilt from the body:
 * it takes over where the painter saw the surface edge-on but this camera sees it face-on, so
 * the painter's view keeps the painted edge and a side view never stretches it. Its alpha is
 * the solid's closed outline, so tuft notches cut from the painter's eye read as cloth from
 * the side. `rimColor` 0 takes only that alpha (back shells keep their own shaded cloth).
 */
function solidMaterial(
  map: THREE.Texture,
  rimMap: THREE.Texture,
  painterEye: THREE.Vector3,
  rimColor: number,
): THREE.ShaderMaterial {
  return new THREE.ShaderMaterial({
    toneMapped: false,
    side: THREE.DoubleSide,
    uniforms: {
      map: { value: map },
      rimMap: { value: rimMap },
      rimColor: { value: rimColor },
      lightDir: { value: LIGHT },
      painterEye: { value: painterEye },
    },
    vertexShader: /* glsl */ `
      varying vec2 vUv;
      varying vec3 vNormal;
      varying vec3 vWorld;
      void main() {
        vUv = uv;
        vNormal = normalize(mat3(modelMatrix) * normal);
        vec4 w = modelMatrix * vec4(position, 1.0);
        vWorld = w.xyz;
        gl_Position = projectionMatrix * viewMatrix * w;
      }
    `,
    fragmentShader: /* glsl */ `
      uniform sampler2D map;
      uniform sampler2D rimMap;
      uniform float rimColor;
      uniform vec3 lightDir;
      uniform vec3 painterEye;
      varying vec2 vUv;
      varying vec3 vNormal;
      varying vec3 vWorld;
      void main() {
        vec4 tex = texture2D(map, vUv);
        vec4 rim = texture2D(rimMap, vUv);
        vec3 n = normalize(vNormal) * (gl_FrontFacing ? 1.0 : -1.0);
        float toPainter = abs(dot(n, normalize(painterEye - vWorld)));
        float toCamera = abs(dot(n, normalize(cameraPosition - vWorld)));
        float side = smoothstep(0.4, 0.15, toPainter) * smoothstep(0.0, 0.25, toCamera - toPainter);
        if (mix(tex.a, rim.a, side) < 0.5) discard;
        vec3 rgb = mix(tex.rgb, rim.rgb, side * rimColor);
        float ndl = dot(n, lightDir);
        float shade = clamp(1.0 + 0.4 * (ndl - lightDir.z), 0.6, 1.1);
        gl_FragColor = vec4(rgb * shade, 1.0);
        #include <colorspace_fragment>
      }
    `,
  })
}

/** Unlit atlas material for phones — no rim pass, no per-pixel lighting. */
function solidBasic(map: THREE.Texture): THREE.MeshBasicMaterial {
  return new THREE.MeshBasicMaterial({
    map,
    side: THREE.DoubleSide,
    toneMapped: false,
    alphaTest: 0.5,
    transparent: false,
  })
}

function Chain({ world }: { world: ArnolfiniWorldData }) {
  const { position, length } = useMemo(() => {
    const a = new THREE.Vector3(...world.chain.from)
    const b = new THREE.Vector3(...world.chain.to)
    return { position: a.clone().add(b).multiplyScalar(0.5), length: a.distanceTo(b) }
  }, [world])
  return (
    <mesh position={position}>
      <cylinderGeometry args={[0.005, 0.005, length, 6]} />
      <meshBasicMaterial color="#3a2d1b" toneMapped={false} />
    </mesh>
  )
}

function glowTexture(): THREE.CanvasTexture {
  const c = document.createElement('canvas')
  c.width = c.height = 64
  const g = c.getContext('2d')!
  const grad = g.createRadialGradient(32, 32, 0, 32, 32, 32)
  grad.addColorStop(0, 'rgba(255,236,190,1)')
  grad.addColorStop(0.18, 'rgba(255,196,110,0.55)')
  grad.addColorStop(1, 'rgba(255,150,60,0)')
  g.fillStyle = grad
  g.fillRect(0, 0, 64, 64)
  const t = new THREE.CanvasTexture(c)
  t.colorSpace = THREE.SRGBColorSpace
  return t
}

/** The single lit candle on the chandelier, breathing. */
function CandleFlame({ at }: { at: [number, number, number] }) {
  const sprite = useRef<THREE.Sprite>(null)
  const texture = useMemo(glowTexture, [])
  useEffect(() => () => texture.dispose(), [texture])
  useFrame(({ clock }) => {
    const s = sprite.current
    if (!s) return
    const t = clock.elapsedTime
    const flicker = 0.85 + 0.1 * Math.sin(t * 13.1) + 0.06 * Math.sin(t * 29.7 + 1.3)
    s.scale.setScalar(0.16 * flicker)
    ;(s.material as THREE.SpriteMaterial).opacity = 0.55 + 0.2 * flicker
  })
  return (
    <sprite ref={sprite} position={at}>
      <spriteMaterial map={texture} blending={THREE.AdditiveBlending} depthWrite={false} transparent toneMapped={false} />
    </sprite>
  )
}

/** Soft daylight falling from the window across the room. */
function WindowLight({ world }: { world: ArnolfiniWorldData }) {
  const material = useMemo(
    () =>
      new THREE.ShaderMaterial({
        transparent: true,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
        side: THREE.DoubleSide,
        toneMapped: false,
        uniforms: { color: { value: new THREE.Color('#fff1d6') }, strength: { value: 0.06 } },
        vertexShader: /* glsl */ `
          varying vec2 vUv;
          varying vec3 vWorld;
          varying vec3 vNormalW;
          void main() {
            vUv = uv;
            vec4 w = modelMatrix * vec4(position, 1.0);
            vWorld = w.xyz;
            vNormalW = normalize(mat3(modelMatrix) * normal);
            gl_Position = projectionMatrix * viewMatrix * w;
          }
        `,
        fragmentShader: /* glsl */ `
          uniform vec3 color;
          uniform float strength;
          varying vec2 vUv;
          varying vec3 vWorld;
          varying vec3 vNormalW;
          void main() {
            float across = smoothstep(0.0, 0.25, vUv.x) * smoothstep(1.0, 0.75, vUv.x);
            float along = pow(1.0 - vUv.y, 1.6);
            vec3 toEye = cameraPosition - vWorld;
            float facing = abs(dot(vNormalW, normalize(toEye)));
            float sheet = clamp(0.2 / max(facing, 0.05), 0.0, 1.0);
            float near = smoothstep(0.6, 2.2, length(toEye));
            gl_FragColor = vec4(color * strength * across * along * sheet * near, 1.0);
          }
        `,
      }),
    [],
  )
  useEffect(() => () => material.dispose(), [material])
  const [cx, cy, cz] = world.window.center
  const [w, h] = world.window.size
  // One beam on low-power; three on desktop.
  const beams = getDeviceProfile().lowPower ? [0] : [-0.3, 0, 0.3]
  return (
    <group>
      {beams.map((dz, i) => (
        <mesh
          key={i}
          material={material}
          position={[cx + 1.3, cy - 0.55, cz + dz * w]}
          rotation={[0, 0, Math.PI / 2 - 0.62]}
        >
          <planeGeometry args={[h * 0.9, 2.8]} />
        </mesh>
      ))}
    </group>
  )
}

function ArnolfiniRoomFull({
  paintingId,
  scene,
  world,
}: {
  paintingId: string
  scene: ArnolfiniScene
  world: ArnolfiniWorldData
}) {
  const roomPages = useSceneTextures(paintingId, scene.pages.room)
  const objPages = useSceneTextures(paintingId, scene.pages.obj)
  const backPages = useSceneTextures(paintingId, scene.pages.objBack)
  const rimPages = useSceneTextures(paintingId, scene.pages.objRim)

  const materials = useMemo(() => {
    const eye = new THREE.Vector3(...world.spawn.position)
    return {
      room: roomPages.map(roomMaterial),
      front: objPages.map((m, i) => solidMaterial(m, rimPages[i], eye, 1)),
      back: backPages.map((m, i) => solidMaterial(m, rimPages[i], eye, 0)),
    }
  }, [roomPages, objPages, backPages, rimPages, world])
  useEffect(
    () => () => {
      materials.room.forEach((m) => m.dispose())
      materials.front.forEach((m) => m.dispose())
      materials.back.forEach((m) => m.dispose())
    },
    [materials],
  )

  return (
    <group>
      {scene.room.map((m) => (
        <mesh key={`room-${m.page}`} geometry={m.geometry} material={materials.room[m.page]} />
      ))}
      {scene.solids.map((s) => (
        <group key={`solid-${s.page}`}>
          <mesh geometry={s.front} material={materials.front[s.page]} />
          <mesh geometry={s.back} material={materials.back[s.page]} />
        </group>
      ))}
      {scene.reliefs.map((r) => (
        <mesh key={`relief-${r.page}`} geometry={r.geometry} material={materials.front[r.page]} />
      ))}
      <Chain world={world} />
      <CandleFlame at={world.candle} />
      <WindowLight world={world} />
    </group>
  )
}

/**
 * Phone / weak-GPU path: no rim atlases, no lit shaders, no window beams / flame.
 * Still the same chamber solids — just cheaper to draw and far less VRAM.
 */
function ArnolfiniRoomLite({
  paintingId,
  scene,
  world,
}: {
  paintingId: string
  scene: ArnolfiniScene
  world: ArnolfiniWorldData
}) {
  const roomPages = useSceneTextures(paintingId, scene.pages.room)
  const objPages = useSceneTextures(paintingId, scene.pages.obj)
  const backPages = useSceneTextures(paintingId, scene.pages.objBack)

  const materials = useMemo(
    () => ({
      room: roomPages.map(roomMaterial),
      front: objPages.map(solidBasic),
      back: backPages.map(solidBasic),
    }),
    [roomPages, objPages, backPages],
  )
  useEffect(
    () => () => {
      materials.room.forEach((m) => m.dispose())
      materials.front.forEach((m) => m.dispose())
      materials.back.forEach((m) => m.dispose())
    },
    [materials],
  )

  return (
    <group>
      {scene.room.map((m) => (
        <mesh key={`room-${m.page}`} geometry={m.geometry} material={materials.room[m.page]} />
      ))}
      {scene.solids.map((s) => (
        <group key={`solid-${s.page}`}>
          <mesh geometry={s.front} material={materials.front[s.page]} />
          <mesh geometry={s.back} material={materials.back[s.page]} />
        </group>
      ))}
      {scene.reliefs.map((r) => (
        <mesh key={`relief-${r.page}`} geometry={r.geometry} material={materials.front[Math.min(r.page, materials.front.length - 1)]} />
      ))}
      <Chain world={world} />
    </group>
  )
}

/**
 * The Arnolfini chamber, walkable. Room shell and furniture carry textures baked offline from
 * the panel; figures / props are closed solids. Low-power devices use a lighter material path.
 */
export function ArnolfiniRoom3D({
  paintingId,
  scene,
  world,
}: {
  paintingId: string
  scene: ArnolfiniScene
  world: ArnolfiniWorldData
}) {
  const low = getDeviceProfile().lowPower
  return low ? (
    <ArnolfiniRoomLite paintingId={paintingId} scene={scene} world={world} />
  ) : (
    <ArnolfiniRoomFull paintingId={paintingId} scene={scene} world={world} />
  )
}
