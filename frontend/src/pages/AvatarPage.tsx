import { useEffect, useRef, useState } from 'react'
import { getAvatar, updateAvatar } from '../api/client'
import { useAvatarStore } from '../store/avatarStore'
import { useAuthStore } from '../store/authStore'
import AvatarViewer, { SkinTonePicker, loadStoredSkinTone, storeSkinTone } from '../components/AvatarViewer'
import type { SkinToneId } from '../components/AvatarViewer'
import { bodyParamsToSmplBetas, smplBetasToBodyParams, DEFAULT_BODY_PARAMS } from '../lib/bodyParamsMapping'
import PhotoPrecisionCapture from '../components/PhotoPrecisionCapture'
import type { BodyParams } from '../types'

// ── Slider row helper ─────────────────────────────────────────────────────

function SliderRow({
  label,
  value,
  min,
  max,
  step,
  onChange,
  leftLabel,
  rightLabel,
  format,
}: {
  label: string
  value: number
  min: number
  max: number
  step: number
  onChange: (v: number) => void
  leftLabel?: string
  rightLabel?: string
  format?: (v: number) => string
}) {
  const display = format ? format(value) : value.toFixed(2)
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-600">{label}</span>
        <span className="font-semibold text-brand-600">{display}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full accent-brand-500"
      />
      {(leftLabel ?? rightLabel) && (
        <div className="flex justify-between text-xs text-gray-400 mt-0.5">
          <span>{leftLabel ?? ''}</span>
          <span>{rightLabel ?? ''}</span>
        </div>
      )}
    </div>
  )
}

// ── Section header ────────────────────────────────────────────────────────

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-3">{title}</p>
      <div className="space-y-4">{children}</div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────

type Tab = 'manuel' | 'photo'

export default function AvatarPage() {
  const { avatar, setAvatar, loading, setLoading } = useAvatarStore()
  const token = useAuthStore((s) => s.token)

  const [bodyParams, setBodyParams] = useState<BodyParams>(DEFAULT_BODY_PARAMS)
  const [gender, setGender]         = useState<'neutral' | 'male' | 'female'>('neutral')
  const [skinTone, setSkinTone]     = useState<SkinToneId>(loadStoredSkinTone)
  const [activeTab, setActiveTab]   = useState<Tab>('manuel')
  const [meshKey, setMeshKey]       = useState(0)
  const [saving, setSaving]         = useState(false)
  const [initDone, setInitDone]     = useState(false)
  const [pageError, setPageError]   = useState('')

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Load avatar on mount
  useEffect(() => {
    if (avatar) return
    setLoading(true)
    getAvatar()
      .then(setAvatar)
      .catch(() => setPageError("Impossible de charger l'avatar."))
      .finally(() => setLoading(false))
  }, [avatar, setAvatar, setLoading])

  // Initialize local body params from avatar (once)
  useEffect(() => {
    if (!avatar || initDone) return
    setGender(avatar.gender)
    setBodyParams(smplBetasToBodyParams(avatar.betas, avatar.height_m, avatar.weight_kg))
    setInitDone(true)
  }, [avatar, initDone])

  // Debounced save to API
  const scheduleReSave = (params: BodyParams, g: typeof gender) => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(async () => {
      setSaving(true)
      try {
        const betas = bodyParamsToSmplBetas(params)
        const saved = await updateAvatar({
          gender: g,
          betas,
          height_m: params.height_m,
          weight_kg: params.weight_kg,
        })
        setAvatar(saved)
        setMeshKey((k) => k + 1)
      } finally {
        setSaving(false)
      }
    }, 400)
  }

  const handleSlider = <K extends keyof BodyParams>(key: K, value: number) => {
    const next = { ...bodyParams, [key]: value }
    setBodyParams(next)
    scheduleReSave(next, gender)
  }

  const handleGender = (g: 'neutral' | 'male' | 'female') => {
    setGender(g)
    scheduleReSave(bodyParams, g)
  }

  if (loading) return <div className="text-center py-16 text-gray-400">Chargement…</div>
  if (!avatar)  return <div className="text-center py-16 text-red-400">{pageError || 'Avatar introuvable.'}</div>

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <h2 className="text-2xl font-bold text-gray-800 mb-6">Mon Avatar</h2>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">

        {/* ── Left: 3D Viewer ─────────────────────────────────────────── */}
        <div className="space-y-3 sticky top-4">
          <AvatarViewer token={token} refreshKey={meshKey} height="520px" skinTone={skinTone} />
          {saving && <p className="text-xs text-gray-400 text-center animate-pulse">Mise à jour du mannequin…</p>}
          <div className="bg-white rounded-xl shadow px-4 py-3">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Couleur de peau</p>
            <SkinTonePicker
              value={skinTone}
              onChange={(id) => { setSkinTone(id); storeSkinTone(id) }}
            />
          </div>
        </div>

        {/* ── Right: Controls ─────────────────────────────────────────── */}
        <div className="bg-white rounded-2xl shadow p-6 space-y-5">

          {/* Gender */}
          <div>
            <p className="text-sm font-semibold text-gray-700 mb-2">Genre</p>
            <div className="flex gap-2">
              {(['neutral', 'male', 'female'] as const).map((g) => (
                <button
                  key={g}
                  onClick={() => handleGender(g)}
                  className={`flex-1 py-2 rounded-lg text-sm font-medium border transition-colors ${
                    gender === g
                      ? 'bg-brand-500 text-white border-brand-500'
                      : 'bg-white text-gray-600 border-gray-300 hover:border-brand-400'
                  }`}
                >
                  {{ neutral: 'Neutre', male: 'Homme', female: 'Femme' }[g]}
                </button>
              ))}
            </div>
          </div>

          {/* Tabs */}
          <div className="border-b border-gray-200">
            <div className="flex gap-0">
              {(['manuel', 'photo'] as Tab[]).map((t) => (
                <button
                  key={t}
                  onClick={() => setActiveTab(t)}
                  className={`px-5 py-2 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === t
                      ? 'border-brand-500 text-brand-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  {t === 'manuel' ? 'Manuel' : 'Photo scan'}
                </button>
              ))}
            </div>
          </div>

          {/* ── Tab Manuel ── */}
          {activeTab === 'manuel' && (
            <div className="space-y-6">

              <Section title="Général">
                <SliderRow
                  label="Taille"
                  value={bodyParams.height_m}
                  min={1.4} max={2.2} step={0.01}
                  onChange={(v) => handleSlider('height_m', v)}
                  leftLabel="1 m 40"
                  rightLabel="2 m 20"
                  format={(v) => `${Math.round(v * 100)} cm`}
                />
                <SliderRow
                  label="Poids"
                  value={bodyParams.weight_kg}
                  min={40} max={200} step={1}
                  onChange={(v) => handleSlider('weight_kg', v)}
                  leftLabel="40 kg"
                  rightLabel="200 kg"
                  format={(v) => `${Math.round(v)} kg`}
                />
              </Section>

              <Section title="Haut du corps">
                <SliderRow
                  label="Corpulence"
                  value={bodyParams.corpulence}
                  min={-1} max={1} step={0.05}
                  onChange={(v) => handleSlider('corpulence', v)}
                  leftLabel="Très mince"
                  rightLabel="Corpulent"
                />
                <SliderRow
                  label="Musculature"
                  value={bodyParams.musculature}
                  min={-1} max={1} step={0.05}
                  onChange={(v) => handleSlider('musculature', v)}
                  leftLabel="Mou"
                  rightLabel="Très musclé"
                />
                <SliderRow
                  label="Largeur d'épaules"
                  value={bodyParams.shoulder_width}
                  min={-1} max={1} step={0.05}
                  onChange={(v) => handleSlider('shoulder_width', v)}
                  leftLabel="Étroites"
                  rightLabel="Larges"
                />
                <SliderRow
                  label="Tour de poitrine"
                  value={bodyParams.chest}
                  min={-1} max={1} step={0.05}
                  onChange={(v) => handleSlider('chest', v)}
                  leftLabel="Plat"
                  rightLabel="Large"
                />
                <SliderRow
                  label="Forme du ventre"
                  value={bodyParams.belly}
                  min={-1} max={1} step={0.05}
                  onChange={(v) => handleSlider('belly', v)}
                  leftLabel="Plat"
                  rightLabel="Rond"
                />
              </Section>

              <Section title="Bas du corps">
                <SliderRow
                  label="Tour de hanche"
                  value={bodyParams.hips}
                  min={-1} max={1} step={0.05}
                  onChange={(v) => handleSlider('hips', v)}
                  leftLabel="Étroites"
                  rightLabel="Larges"
                />
                <SliderRow
                  label="Fesses"
                  value={bodyParams.fesses}
                  min={-1} max={1} step={0.05}
                  onChange={(v) => handleSlider('fesses', v)}
                  leftLabel="Plates"
                  rightLabel="Volumineuses"
                />
                <SliderRow
                  label="Longueur des jambes"
                  value={bodyParams.leg_length}
                  min={-1} max={1} step={0.05}
                  onChange={(v) => handleSlider('leg_length', v)}
                  leftLabel="Courtes"
                  rightLabel="Longues"
                />
                <SliderRow
                  label="Forme des jambes"
                  value={bodyParams.leg_shape}
                  min={-1} max={1} step={0.05}
                  onChange={(v) => handleSlider('leg_shape', v)}
                  leftLabel="Fines"
                  rightLabel="Épaisses"
                />
              </Section>

              <Section title="Membres supérieurs">
                <SliderRow
                  label="Longueur des bras"
                  value={bodyParams.arm_length}
                  min={-1} max={1} step={0.05}
                  onChange={(v) => handleSlider('arm_length', v)}
                  leftLabel="Courts"
                  rightLabel="Longs"
                />
              </Section>

            </div>
          )}

          {/* ── Tab Photo scan ── */}
          {activeTab === 'photo' && (
            <PhotoPrecisionCapture
              initialHeight={Math.round(bodyParams.height_m * 100)}
              initialWeight={Math.round(bodyParams.weight_kg)}
              onComplete={(params, _confidence) => {
                setBodyParams(params)
                scheduleReSave(params, gender)
                setActiveTab('manuel')
              }}
              onCancel={() => setActiveTab('manuel')}
            />
          )}

        </div>
      </div>
    </div>
  )
}
