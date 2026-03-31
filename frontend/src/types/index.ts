export interface User {
  id: string
  email: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: User
}

export interface Avatar {
  id: string
  gender: 'neutral' | 'male' | 'female'
  betas: number[]
  height_m: number
  weight_kg: number
}

export interface AvatarUpdate {
  gender?: 'neutral' | 'male' | 'female'
  betas?: number[]
  height_m?: number
  weight_kg?: number
}

export interface Measurements {
  height_m: number
  chest_m: number
  waist_m: number
  hips_m: number
}

export interface Garment {
  id: string
  name: string
  category: string
  description: string
  sizes: string[]
  thumbnail_url: string | null
}

export interface GarmentList {
  items: Garment[]
  total: number
}

export interface BodyParams {
  height_m: number        // 1.40–2.20 m
  weight_kg: number       // 40–200 kg
  corpulence: number      // -1 (très mince) à +1 (très corpulent)
  musculature: number     // -1 (mou) à +1 (très musclé)
  shoulder_width: number  // -1 (étroites) à +1 (larges)
  chest: number           // -1 (plat) à +1 (large)
  belly: number           // -1 (plat) à +1 (rond)
  hips: number            // -1 (étroites) à +1 (larges)
  fesses: number          // -1 (plates) à +1 (volumineuses)
  arm_length: number      // -1 (courts) à +1 (longs)
  leg_length: number      // -1 (courtes) à +1 (longues)
  leg_shape: number       // -1 (fines) à +1 (épaisses)
}

export interface PhotoEstimation {
  id: string
  gender: 'neutral' | 'male' | 'female'
  betas: number[]
  height_m: number
  weight_kg: number
  confidence: number
  message: string
}

export interface FittingResult {
  garment_id: string
  garment_name: string
  garment_category: string
  recommended_size: string
  available_sizes: string[]
  measurements: {
    height_cm: number
    chest_cm: number
    waist_cm: number
    hips_cm: number
  }
  smpl_available: boolean
}
