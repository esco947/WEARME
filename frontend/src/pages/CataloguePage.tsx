import { useEffect, useState } from 'react'
import { listGarments } from '../api/client'
import ProductCard from '../components/ProductCard'
import type { Garment } from '../types'

const CATEGORIES = [
  { key: 'Tous',    label: 'Tous' },
  { key: 't-shirt', label: 'T-Shirts' },
  { key: 'jacket',  label: 'Vestes' },
  { key: 'pants',   label: 'Pantalons' },
  { key: 'hoodie',  label: 'Hoodies' },
  { key: 'dress',   label: 'Robes' },
]

export default function CataloguePage() {
  const [garments, setGarments] = useState<Garment[]>([])
  const [filter, setFilter] = useState('Tous')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    listGarments()
      .then((data) => setGarments(data.items))
      .finally(() => setLoading(false))
  }, [])

  const filtered = filter === 'Tous' ? garments : garments.filter((g) => g.category === filter)

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-gray-800">Catalogue</h2>
        <p className="text-gray-500 text-sm mt-1">{garments.length} vêtements disponibles</p>
      </div>

      {/* Category filter */}
      <div className="flex gap-2 flex-wrap mb-8">
        {CATEGORIES.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setFilter(key)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium border transition-colors ${
              filter === key
                ? 'bg-brand-500 text-white border-brand-500'
                : 'bg-white text-gray-600 border-gray-200 hover:border-brand-400 hover:text-brand-600'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="bg-gray-100 rounded-2xl h-52 animate-pulse" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center text-gray-400 py-16">Aucun vêtement trouvé.</div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
          {filtered.map((g) => <ProductCard key={g.id} garment={g} />)}
        </div>
      )}
    </div>
  )
}
