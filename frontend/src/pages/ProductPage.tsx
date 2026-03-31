import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getGarment } from '../api/client'
import type { Garment } from '../types'

const CATEGORY_LABELS: Record<string, string> = {
  'tshirt': 'T-Shirt', 't-shirt': 'T-Shirt',
  jacket: 'Veste', pants: 'Pantalon',
  hoodie: 'Hoodie', dress: 'Robe',
}

export default function ProductPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [garment, setGarment] = useState<Garment | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    getGarment(id)
      .then(setGarment)
      .catch(() => navigate('/catalogue'))
      .finally(() => setLoading(false))
  }, [id, navigate])

  if (loading) return <div className="text-center py-16 text-gray-400">Chargement...</div>
  if (!garment) return null

  return (
    <div className="max-w-3xl mx-auto px-4 py-10">
      <button onClick={() => navigate(-1)} className="text-brand-500 hover:underline text-sm mb-6 inline-block">
        ← Retour au catalogue
      </button>

      <div className="bg-white rounded-2xl shadow p-8">
        {/* Placeholder image */}
        <div className="w-full h-64 bg-gradient-to-br from-brand-100 to-brand-50 rounded-xl flex items-center justify-center mb-6">
          <span className="text-6xl">
            {{ 't-shirt': '👕', jacket: '🧥', pants: '👖', hoodie: '🧥', dress: '👗' }[garment.category] ?? '👔'}
          </span>
        </div>

        <span className="text-xs font-semibold uppercase tracking-widest text-brand-500">
          {CATEGORY_LABELS[garment.category] ?? garment.category}
        </span>
        <h1 className="text-3xl font-bold text-gray-800 mt-1 mb-3">{garment.name}</h1>
        <p className="text-gray-600 mb-6">{garment.description}</p>

        <div>
          <p className="text-sm font-medium text-gray-700 mb-2">Tailles disponibles</p>
          <div className="flex gap-2 flex-wrap">
            {garment.sizes.map((s) => (
              <span key={s} className="px-3 py-1 border border-gray-300 rounded-lg text-sm font-medium text-gray-700">
                {s}
              </span>
            ))}
          </div>
        </div>

        <button
          onClick={() => navigate(`/fitting/${garment.id}`)}
          className="mt-8 w-full bg-brand-500 hover:bg-brand-600 text-white font-semibold py-3 rounded-xl transition-colors"
        >
          Essayer sur mon avatar
        </button>
      </div>
    </div>
  )
}
