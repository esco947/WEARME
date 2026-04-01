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
  // Phase 2: anatomical params (subset of 55 keys)
  params?: Record<string, number>
  locked?: string[]
}

export interface FullMeasurements {
  height_m: number
  chest_m: number
  underbust_m: number
  waist_m: number
  abdomen_m: number
  hip_m: number
  hips_m: number
  neck_m: number
  shoulder_width_m: number
  arm_length_m: number
  upper_arm_m: number
  forearm_m: number
  wrist_m: number
  inseam_m: number
  outseam_m: number
  thigh_m: number
  calf_m: number
  ankle_m: number
  front_length_m: number
  back_length_m: number
  dart_width_m: number
  chest_with_ease_m: number
  waist_with_ease_m: number
  hip_with_ease_m: number
  eu_size_top: string
  eu_size_bottom: string
  us_size_top: string
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
