import { useEffect, useRef, useState } from 'react'
import { updateSliders } from '../api/client'
import type { Avatar } from '../types'

const SLIDERS = [
  { key: 'height',              label: 'Taille',           min: 150, max: 210, step: 0.5, unit: 'cm' },
  { key: 'chest_circumference', label: 'Tour de poitrine', min: 75,  max: 135, step: 0.5, unit: 'cm' },
  { key: 'waist_circumference', label: 'Tour de taille',   min: 60,  max: 120, step: 0.5, unit: 'cm' },
  { key: 'hip_circumference',   label: 'Tour de hanches',  min: 80,  max: 130, step: 0.5, unit: 'cm' },
  { key: 'shoulder_width',      label: 'Largeur épaules',  min: 35,  max: 55,  step: 0.5, unit: 'cm' },
  { key: 'inseam',              label: 'Entrejambe',       min: 65,  max: 95,  step: 0.5, unit: 'cm' },
] as const

type SliderKey = typeof SLIDERS[number]['key']

interface Props {
  avatar: Avatar
  onUpdate: (avatar: Avatar) => void
}

function measurementsToCm(measurements: Record<string, number>): Record<SliderKey, number> {
  const defaults: Record<SliderKey, number> = {
    height: 175,
    chest_circumference: 99,
    waist_circumference: 84,
    hip_circumference: 97,
    shoulder_width: 45,
    inseam: 81,
  }
  const result = { ...defaults }
  for (const s of SLIDERS) {
    const val = measurements[s.key]
    if (val !== undefined) result[s.key] = Math.round(val * 100 * 2) / 2
  }
  return result
}

// Animated progress bar — fills over `durationMs`, stops at 90% until done
function ProgressBar({ active, durationMs = 15000 }: { active: boolean; durationMs?: number }) {
  const [progress, setProgress] = useState(0)
  const rafRef = useRef<number | null>(null)
  const startRef = useRef<number | null>(null)

  useEffect(() => {
    if (!active) {
      setProgress(0)
      startRef.current = null
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
      return
    }

    const tick = (now: number) => {
      if (!startRef.current) startRef.current = now
      const elapsed = now - startRef.current
      // Ease toward 90% over durationMs, never reaches 100% until done
      const pct = 90 * (1 - Math.exp(-3 * elapsed / durationMs))
      setProgress(pct)
      rafRef.current = requestAnimationFrame(tick)
    }
    rafRef.current = requestAnimationFrame(tick)
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current) }
  }, [active, durationMs])

  if (!active) return null

  return (
    <div className="w-full bg-brand-100 rounded-full h-1.5 overflow-hidden">
      <div
        className="h-full bg-brand-500 rounded-full transition-none"
        style={{ width: `${progress}%` }}
      />
    </div>
  )
}

export default function SliderPanel({ avatar, onUpdate }: Props) {
  const [values, setValues] = useState<Record<SliderKey, number>>(
    () => measurementsToCm(avatar.measurements)
  )
  const [saving, setSaving] = useState(false)
  const [dirty, setDirty]   = useState(false)
  const [error, setError]   = useState<string | null>(null)

  useEffect(() => {
    setValues(measurementsToCm(avatar.measurements))
    setDirty(false)
    setError(null)
  }, [avatar.id, avatar.gender])

  const handleChange = (key: SliderKey, valueCm: number) => {
    setValues((prev) => ({ ...prev, [key]: valueCm }))
    setDirty(true)
    setError(null)
  }

  const handleGenerate = async () => {
    setSaving(true)
    setError(null)
    try {
      const targets: Record<string, number> = {}
      for (const [k, v] of Object.entries(values)) {
        targets[k] = v / 100
      }
      const updated = await updateSliders(targets)
      onUpdate(updated)
      setDirty(false)
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(msg ?? 'Erreur lors de la génération. Réessaie.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-4">
      {SLIDERS.map((s) => (
        <div key={s.key}>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-600">{s.label}</span>
            <span className={`font-semibold ${dirty ? 'text-amber-500' : 'text-brand-600'}`}>
              {values[s.key].toFixed(1)} {s.unit}
            </span>
          </div>
          <input
            type="range"
            min={s.min}
            max={s.max}
            step={s.step}
            value={values[s.key]}
            onChange={(e) => handleChange(s.key, parseFloat(e.target.value))}
            disabled={saving}
            className="w-full accent-brand-500 disabled:opacity-50"
          />
          <div className="flex justify-between text-xs text-gray-400 mt-0.5">
            <span>{s.min} {s.unit}</span>
            <span>{s.max} {s.unit}</span>
          </div>
        </div>
      ))}

      {dirty && !saving && (
        <p className="text-xs text-amber-500 text-center">Modifications non appliquées</p>
      )}

      <div className="space-y-2 pt-1">
        <button
          onClick={handleGenerate}
          disabled={saving}
          className="w-full py-2.5 bg-brand-500 text-white rounded-lg font-medium text-sm
                     hover:bg-brand-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors
                     flex items-center justify-center gap-2"
        >
          {saving && (
            <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
          )}
          {saving ? 'Génération en cours…' : 'Générer le mannequin'}
        </button>

        <ProgressBar active={saving} durationMs={15000} />

        {saving && (
          <p className="text-xs text-gray-400 text-center">
            Optimisation SMPL en cours, cela peut prendre 5 à 20 secondes…
          </p>
        )}
      </div>

      {error && (
        <p className="text-sm text-red-500 bg-red-50 rounded-lg px-3 py-2">{error}</p>
      )}
    </div>
  )
}
