import { create } from 'zustand'
import type { Avatar } from '../types'

interface AvatarState {
  gender: 'male' | 'female'
  betas: number[]
  measurements: Record<string, number>
  meshVersion: number
  loading: boolean
  error: string | null
  setFromAvatar: (avatar: Avatar) => void
  incrementMeshVersion: () => void
  setLoading: (v: boolean) => void
  setError: (e: string | null) => void
  reset: () => void
}

export const useAvatarStore = create<AvatarState>((set) => ({
  gender: 'male',
  betas: Array(10).fill(0),
  measurements: {},
  meshVersion: 0,
  loading: false,
  error: null,
  setFromAvatar: (avatar) =>
    set((s) => ({
      gender: avatar.gender,
      betas: avatar.betas,
      measurements: avatar.measurements,
      meshVersion: s.meshVersion + 1,
    })),
  incrementMeshVersion: () => set((s) => ({ meshVersion: s.meshVersion + 1 })),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  reset: () =>
    set({ gender: 'male', betas: Array(10).fill(0), measurements: {}, meshVersion: 0, loading: false, error: null }),
}))
