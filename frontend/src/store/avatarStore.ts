import { create } from 'zustand'
import type { Avatar, Measurements } from '../types'

interface AvatarState {
  avatar: Avatar | null
  measurements: Measurements | null
  loading: boolean
  setAvatar: (avatar: Avatar) => void
  setMeasurements: (m: Measurements) => void
  setLoading: (v: boolean) => void
  reset: () => void
}

export const useAvatarStore = create<AvatarState>((set) => ({
  avatar: null,
  measurements: null,
  loading: false,
  setAvatar: (avatar) => set({ avatar }),
  setMeasurements: (measurements) => set({ measurements }),
  setLoading: (loading) => set({ loading }),
  reset: () => set({ avatar: null, measurements: null, loading: false }),
}))
