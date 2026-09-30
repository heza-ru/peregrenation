import { create } from 'zustand'

type WorldUiState = {
  pointerLocked: boolean
  /** True once the visitor has started exploring (lock on desktop, first drag/stick on mobile). */
  exploring: boolean
  touchPrimary: boolean
  /** Virtual stick: x = strafe, y = forward (both -1…1) */
  touchMove: { x: number; y: number }
  nearEntityId: string | null
  nearEntityLabel: string | null
  nearCuriosityTitle: string | null
  nearCuriosityTeaser: string | null
  discoveredIds: string[]
  setPointerLocked: (locked: boolean) => void
  setExploring: (exploring: boolean) => void
  setTouchPrimary: (touchPrimary: boolean) => void
  setTouchMove: (x: number, y: number) => void
  setNearEntity: (
    id: string | null,
    label: string | null,
    curiosityTitle?: string | null,
    teaser?: string | null,
  ) => void
  markDiscovered: (id: string) => void
}

export const useWorldStore = create<WorldUiState>((set, get) => ({
  pointerLocked: false,
  exploring: false,
  touchPrimary: false,
  touchMove: { x: 0, y: 0 },
  nearEntityId: null,
  nearEntityLabel: null,
  nearCuriosityTitle: null,
  nearCuriosityTeaser: null,
  discoveredIds: [],
  setPointerLocked: (pointerLocked) => set({ pointerLocked, exploring: pointerLocked || get().exploring }),
  setExploring: (exploring) => set({ exploring }),
  setTouchPrimary: (touchPrimary) => set({ touchPrimary }),
  setTouchMove: (x, y) => set({ touchMove: { x, y } }),
  setNearEntity: (nearEntityId, nearEntityLabel, nearCuriosityTitle = null, nearCuriosityTeaser = null) =>
    set({ nearEntityId, nearEntityLabel, nearCuriosityTitle, nearCuriosityTeaser }),
  markDiscovered: (id) => {
    if (get().discoveredIds.includes(id)) return
    set({ discoveredIds: [...get().discoveredIds, id] })
  },
}))
