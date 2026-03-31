import axios from 'axios'
import type { Avatar, AvatarUpdate, FittingResult, GarmentList, Garment, Measurements, PhotoEstimation, TokenResponse } from '../types'

const api = axios.create({ baseURL: '/api' })

// Inject JWT token from localStorage on every request
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

export const updateAvatar = (data: AvatarUpdate) =>
  api.put<Avatar>('/avatar', data).then((r) => r.data)

export const getMeasurements = () =>
  api.get<Measurements>('/avatar/measurements').then((r) => r.data)

export const getMeshUrl = () => '/api/avatar/mesh'

// Garments
export const listGarments = () =>
  api.get<GarmentList>('/garments').then((r) => r.data)

export const getGarment = (id: string) =>
  api.get<Garment>(`/garments/${id}`).then((r) => r.data)

// Fitting
export const fitGarment = (garmentId: string) =>
  api.post<FittingResult>(`/fitting/${garmentId}`).then((r) => r.data)

// Photo scan — estimates avatar body params from uploaded photos
export const avatarFromPhoto = (formData: FormData) =>
  api.post<PhotoEstimation>('/avatar/from-photo', formData).then((r) => r.data)
