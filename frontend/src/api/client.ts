import axios from 'axios'
import type { Avatar, MeasurementsResponse, TokenResponse } from '../types'

const api = axios.create({ baseURL: '/api' })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('wearme_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Auth
export const register = (email: string, password: string) =>
  api.post<TokenResponse>('/auth/register', { email, password }).then((r) => r.data)

export const login = (email: string, password: string) =>
  api.post<TokenResponse>('/auth/login', { email, password }).then((r) => r.data)

export const getMe = () =>
  api.get('/me').then((r) => r.data)

// Avatar
export const getAvatar = () =>
  api.get<Avatar>('/avatar').then((r) => r.data)

export const setGender = (gender: 'male' | 'female') =>
  api.put<Avatar>('/avatar/gender', { gender }).then((r) => r.data)

/** targets: { measurement_key: value_in_metres } */
export const updateSliders = (targets: Record<string, number>) =>
  api.put<Avatar>('/avatar/sliders', { targets }).then((r) => r.data)

export const photoFit = (formData: FormData) =>
  api.post<Avatar>('/avatar/photo-fit', formData).then((r) => r.data)

export const getMeasurements = () =>
  api.get<MeasurementsResponse>('/avatar/measurements').then((r) => r.data)

export const getMeshUrl = () => '/api/avatar/mesh'
