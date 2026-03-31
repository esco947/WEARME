/// <reference types="@react-three/fiber" />
import { Suspense, useEffect, useRef, useState } from 'react'
import { Canvas, useLoader } from '@react-three/fiber'
import { OrbitControls, Environment } from '@react-three/drei'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import * as THREE from 'three'
import axios from 'axios'

// ── Skin tone palette ─────────────────────────────────────────────────────

export const SKIN_TONES = [
  { id: 'very-light', label: 'Très clair',   hex: '#FDDBB4' },
  { id: 'light',      label: 'Clair',        hex: '#E8B990' },
  { id: 'medium',     label: 'Moyen clair',  hex: '#C68642' },
  { id: 'tan',        label: 'Moyen',        hex: '#A0522D' },
  { id: 'dark',       label: 'Foncé',        hex: '#6B3A2A' },
  { id: 'very-dark',  label: 'Très foncé',   hex: '#3B1F0F' },
] as const

export type SkinToneId = (typeof SKIN_TONES)[number]['id']

const SKIN_STORAGE_KEY = 'wearme_skin_tone'

// ── Authenticated GLB fetcher ─────────────────────────────────────────────

function useAuthGlb(token: string | null, refreshKey: number) {
  const [url, setUrl]         = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState(false)
  const prevUrl               = useRef<string | null>(null)

  useEffect(() => {
    if (!token) return
    setLoading(true)
    setError(false)
    axios
      .get('/api/avatar/mesh', {
        responseType: 'arraybuffer',
        headers: { Authorization: `Bearer ${token}` },
      })
      .then((res) => {
        const bytes = new Uint8Array(res.data as ArrayBuffer)
        // Validate GLB magic bytes: "glTF"
        if (bytes[0] !== 0x67 || bytes[1] !== 0x6C || bytes[2] !== 0x54 || bytes[3] !== 0x46) {
          setError(true)
          return
        }
        const blob      = new Blob([res.data as ArrayBuffer], { type: 'model/gltf-binary' })
        const objectUrl = URL.createObjectURL(blob)
        if (prevUrl.current) URL.revokeObjectURL(prevUrl.current)
        prevUrl.current = objectUrl
        setUrl(objectUrl)
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }, [token, refreshKey])

  useEffect(() => () => { if (prevUrl.current) URL.revokeObjectURL(prevUrl.current) }, [])

  return { url, loading, error }
}

// ── 3D model ──────────────────────────────────────────────────────────────

function AvatarModel({ url, skinColor }: { url: string; skinColor: string }) {
  const gltf = useLoader(GLTFLoader, url)

  useEffect(() => {
    const color = new THREE.Color(skinColor)
    gltf.scene.traverse((obj) => {
      if ('isMesh' in obj && obj.isMesh) {
        const mesh = obj as unknown as THREE.Mesh
        mesh.material = new THREE.MeshStandardMaterial({
          color,
          roughness: 0.75,
          metalness: 0.0,
        })
        mesh.castShadow    = true
        mesh.receiveShadow = true
      }
    })
    const box    = new THREE.Box3().setFromObject(gltf.scene as unknown as THREE.Object3D)
    const center = box.getCenter(new THREE.Vector3())
    const size   = box.getSize(new THREE.Vector3())
    gltf.scene.position.x -= center.x
    gltf.scene.position.z -= center.z
    gltf.scene.position.y -= center.y + size.y / 2
  }, [gltf.scene, skinColor])

  return <primitive object={gltf.scene} />
}

// ── Skin tone picker (exported for use in AvatarPage) ────────────────────

interface SkinPickerProps {
  value: SkinToneId
  onChange: (id: SkinToneId) => void
}

export function SkinTonePicker({ value, onChange }: SkinPickerProps) {
  return (
    <div className="flex gap-2 flex-wrap">
      {SKIN_TONES.map((t) => (
        <button
          key={t.id}
          title={t.label}
          onClick={() => onChange(t.id)}
          style={{ backgroundColor: t.hex }}
          className={`w-7 h-7 rounded-full border-2 transition-transform hover:scale-110 ${
            value === t.id ? 'border-brand-500 scale-110 shadow-md' : 'border-white/60'
          }`}
        />
      ))}
    </div>
  )
}

// ── Public component ──────────────────────────────────────────────────────

interface Props {
  token: string | null
  refreshKey?: number
  height?: string
  skinTone?: SkinToneId
}

export default function AvatarViewer({ token, refreshKey = 0, height = '400px', skinTone }: Props) {
  const { url, loading, error } = useAuthGlb(token, refreshKey)

  const tone   = skinTone ?? 'light'
  const hexColor = SKIN_TONES.find((t) => t.id === tone)?.hex ?? '#E8B990'

  return (
    <div
      style={{ height }}
      className="w-full rounded-xl overflow-hidden bg-gradient-to-b from-slate-700 to-slate-900 relative"
    >
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center text-slate-400 text-sm z-10">
          <div className="text-center space-y-2">
            <div className="w-8 h-8 border-2 border-slate-400 border-t-brand-400 rounded-full animate-spin mx-auto" />
            <p>Génération du mannequin…</p>
          </div>
        </div>
      )}
      {error && (
        <div className="absolute inset-0 flex items-center justify-center z-10">
          <div className="text-center text-slate-400">
            <div className="text-5xl mb-2">🧍</div>
            <p className="text-sm">Modèle 3D indisponible</p>
          </div>
        </div>
      )}
      {url && !error && (
        <Canvas
          shadows
          camera={{ position: [0, 0.9, 2.8], fov: 42 }}
          gl={{ antialias: true, toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.1 }}
        >
          {/* Ambiance très faible pour des ombres profondes */}
          <ambientLight intensity={0.15} />

          {/* Key light — haut gauche avant : définit les formes principales */}
          <directionalLight
            position={[-2.5, 5, 3]}
            intensity={2.0}
            castShadow
            shadow-mapSize={[1024, 1024]}
          />

          {/* Fill light — droite, légèrement devant : atténue les ombres dures */}
          <directionalLight position={[3, 3, 1]} intensity={0.6} />

          {/* Rim light — arrière bas : sépare le mannequin du fond */}
          <directionalLight position={[0, -1, -4]} intensity={0.4} color="#b0c8ff" />

          {/* Environment pour les reflets subtils sur la peau */}
          <Environment preset="warehouse" />

          <Suspense fallback={null}>
            <AvatarModel url={url} skinColor={hexColor} />
          </Suspense>

          <OrbitControls
            enablePan={false}
            minDistance={1.2}
            maxDistance={6}
            minPolarAngle={0.1}
            maxPolarAngle={Math.PI - 0.1}
            target={[0, 0, 0]}
          />
        </Canvas>
      )}
    </div>
  )
}

// Re-export stored skin tone helpers
export function loadStoredSkinTone(): SkinToneId {
  return (localStorage.getItem(SKIN_STORAGE_KEY) as SkinToneId | null) ?? 'light'
}

export function storeSkinTone(id: SkinToneId) {
  localStorage.setItem(SKIN_STORAGE_KEY, id)
}
