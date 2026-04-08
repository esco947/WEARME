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
  gender: 'male' | 'female'
  betas: number[]
  measurements: Record<string, number>
}

export interface MeasurementsResponse {
  measurements: Record<string, number>
}
