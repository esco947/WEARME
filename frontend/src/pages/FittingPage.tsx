import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { fitGarment, getGarment } from '../api/client'
import { useAuthStore } from '../store/authStore'
import AvatarViewer from '../components/AvatarViewer'
import type { FittingResult, Garment } from '../types'

const EMOJI: Record<string, string> = {
  't-shirt': '👕', jacket: '🧥', pants: '👖', hoodie: '🧥', dress: '👗',
}

const SIZE_COLORS: Record<string, string> = {
  XS: 'bg-purple-100 text-purple-700',
  S:  'bg-blue-100 text-blue-700',
  M:  'bg-green-100 text-green-700',
  L:  'bg-yellow-100 text-yellow-700',
  XL: 'bg-orange-100 text-orange-700',
  XXL:'bg-red-100 text-red-700',
}

export default function FittingPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const token = useAuthStore((s) => s.token)
  const [garment, setGarment] = useState<Garment | null>(null)
  const [fitting, setFitting] = useState<FittingResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!id) return
    Promise.all([getGarment(id), fitGarment(id)])
      .then(([g, f]) => { setGarment(g); setFitting(f) })
      .catch(() => setError("Impossible de charger l'essayage."))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <div className="text-center py-16 text-gray-400">Analyse en cours…</div>
  if (error || !garment || !fitting) return (
    <div className="text-center py-16 text-red-400">
      <p>{error}</p>
      <button onClick={() => navigate(-1)} className="mt-4 text-brand-500 hover:underline text-sm">← Retour</button>
    </div>
  )

  const { measurements, recommended_size, available_sizes, smpl_available } = fitting
  const sizeColor = SIZE_COLORS[recommended_size] ?? 'bg-brand-100 text-brand-700'

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <button onClick={() => navigate(-1)} className="text-brand-500 hover:underline text-sm mb-6 inline-block">
        ← Retour
      </button>

      <h2 className="text-2xl font-bold text-gray-800 mb-6">Essayage virtuel</h2>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Left — Avatar 3D */}
        <div>
          <AvatarViewer token={token} height="480px" />
          {!smpl_available && (
            <p className="text-xs text-amber-600 mt-2 text-center">
              Mesures estimées — modèle SMPL non disponible
            </p>
          )}
        </div>

        {/* Right — Fitting result */}
        <div className="space-y-4">
          {/* Garment info */}
          <div className="bg-white rounded-2xl shadow p-6">
            <div className="flex items-center gap-4 mb-4">
              <span className="text-5xl">{EMOJI[garment.category] ?? '👔'}</span>
              <div>
                <p className="text-xs font-semibold uppercase tracking-widest text-brand-500">{garment.category}</p>
                <h3 className="text-xl font-bold text-gray-800">{garment.name}</h3>
              </div>
            </div>
            <p className="text-gray-600 text-sm">{garment.description}</p>
          </div>

          {/* Size recommendation */}
          <div className="bg-white rounded-2xl shadow p-6">
            <p className="text-sm font-semibold text-gray-700 mb-4">Taille recommandée</p>
            <div className="flex items-center gap-3 mb-4">
              <span className={`text-3xl font-bold px-5 py-2 rounded-xl ${sizeColor}`}>
                {recommended_size}
              </span>
              <p className="text-sm text-gray-500">
                Calculée à partir de vos mensurations
              </p>
            </div>

            {/* All sizes */}
            <div className="flex gap-2 flex-wrap">
              {available_sizes.map((s) => (
                <span
                  key={s}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium border-2 transition-colors ${
                    s === recommended_size
                      ? 'border-brand-500 text-brand-600 bg-brand-50'
                      : 'border-gray-200 text-gray-500'
                  }`}
                >
                  {s}
                </span>
              ))}
            </div>
          </div>

          {/* Measurements */}
          <div className="bg-white rounded-2xl shadow p-6">
            <p className="text-sm font-semibold text-gray-700 mb-3">Vos mensurations</p>
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: 'Hauteur',  value: `${measurements.height_cm.toFixed(0)} cm` },
                { label: 'Poitrine', value: `${measurements.chest_cm.toFixed(0)} cm` },
                { label: 'Taille',   value: `${measurements.waist_cm.toFixed(0)} cm` },
                { label: 'Hanches',  value: `${measurements.hips_cm.toFixed(0)} cm` },
              ].map(({ label, value }) => (
                <div key={label} className="bg-gray-50 rounded-lg px-3 py-2 text-center">
                  <p className="text-xs text-gray-500">{label}</p>
                  <p className="font-semibold text-gray-700">{value}</p>
                </div>
              ))}
            </div>
          </div>

          <button
            onClick={() => navigate('/avatar')}
            className="w-full bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium py-2.5 rounded-xl transition-colors text-sm"
          >
            Modifier mon avatar
          </button>
        </div>
      </div>
    </div>
  )
}
