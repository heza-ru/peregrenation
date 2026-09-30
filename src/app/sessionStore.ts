import { create } from 'zustand'

export type BuildStatus = 'idle' | 'processing' | 'ready' | 'error'

type SessionState = {
  paintingId: string | null
  sourceImage: string | null
  buildStatus: BuildStatus
  buildMessage: string
  setPainting: (id: string, source?: string | null) => void
  setBuildStatus: (status: BuildStatus, message?: string) => void
  reset: () => void
}

export const useSessionStore = create<SessionState>((set) => ({
  paintingId: null,
  sourceImage: null,
  buildStatus: 'idle',
  buildMessage: '',
  setPainting: (paintingId, sourceImage = null) =>
    set({ paintingId, sourceImage, buildStatus: 'idle', buildMessage: '' }),
  setBuildStatus: (buildStatus, buildMessage = '') => set({ buildStatus, buildMessage }),
  reset: () =>
    set({
      paintingId: null,
      sourceImage: null,
      buildStatus: 'idle',
      buildMessage: '',
    }),
}))
