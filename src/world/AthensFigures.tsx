import { useEffect, useMemo } from 'react'
import * as THREE from 'three'
import { setAthensFigureColliders } from './athensHallConfig'
import type { AthensScene } from './athensScene'
import type { AthensWorldData } from './athensWorldData'
import { getDeviceProfile } from './deviceProfile'
import { useSceneTextures } from './sceneTextures'

/** Key light from the upper left, as in the fresco; a surface facing the painter keeps its painted value. */
const LIGHT = new THREE.Vector3(-0.45, 0.55, 0.7).normalize()

function figureMaterial(map: THREE.Texture): THREE.ShaderMaterial {
  return new THREE.ShaderMaterial({
    toneMapped: false,
    uniforms: { map: { value: map }, lightDir: { value: LIGHT } },
    vertexShader: /* glsl */ `
      varying vec2 vUv;
      varying vec3 vNormal;
      void main() {
        vUv = uv;
        vNormal = normal;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: /* glsl */ `
      uniform sampler2D map;
      uniform vec3 lightDir;
      varying vec2 vUv;
      varying vec3 vNormal;
      void main() {
        vec4 tex = texture2D(map, vUv);
        if (tex.a < 0.5) discard;
        vec3 n = normalize(vNormal);
        float ndl = dot(n, lightDir);
        float shade = clamp(1.0 + 0.45 * (ndl - lightDir.z), 0.55, 1.12);
        gl_FragColor = vec4(tex.rgb * shade, 1.0);
        #include <colorspace_fragment>
      }
    `,
  })
}

function figureBasic(map: THREE.Texture): THREE.MeshBasicMaterial {
  return new THREE.MeshBasicMaterial({
    map,
    toneMapped: false,
    alphaTest: 0.5,
    side: THREE.FrontSide,
  })
}

/**
 * Figures as inflated, rounded bodies (circular cross-section from each silhouette), fixed in
 * hall space. Fronts carry the fresco; backs a softened version. Low-power uses unlit materials.
 */
export function AthensFigures({
  world,
  scene,
  paintingId,
}: {
  world: AthensWorldData
  scene: AthensScene
  paintingId: string
}) {
  const fronts = useSceneTextures(paintingId, scene.index.pages.fig)
  const backs = useSceneTextures(paintingId, scene.index.pages.figBack)
  const low = getDeviceProfile().lowPower

  const materials = useMemo(() => {
    if (low) {
      return { front: fronts.map(figureBasic), back: backs.map(figureBasic) }
    }
    return { front: fronts.map(figureMaterial), back: backs.map(figureMaterial) }
  }, [fronts, backs, low])
  useEffect(
    () => () => {
      materials.front.forEach((m) => m.dispose())
      materials.back.forEach((m) => m.dispose())
    },
    [materials],
  )

  useEffect(() => {
    setAthensFigureColliders(world.figures.filter((f) => f.tier !== 'statue').map((f) => f.collider))
    return () => setAthensFigureColliders([])
  }, [world])

  return (
    <group>
      {scene.figures.map((f) => (
        <group key={f.page}>
          <mesh geometry={f.front} material={materials.front[f.page]} />
          <mesh geometry={f.back} material={materials.back[f.page]} />
        </group>
      ))}
    </group>
  )
}
