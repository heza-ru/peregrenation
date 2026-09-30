/** Hero parallax plane transforms (CSS px), written by Hero and drawn by the scene canvas */
export type PlaneState = { x: number; y: number; scale: number; pullX: number; pullY: number }

export const heroBus: { planes: PlaneState[] } = {
  planes: [],
}
