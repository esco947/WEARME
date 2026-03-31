import { useNavigate } from 'react-router-dom'
import type { Garment } from '../types'

const EMOJI: Record<string, string> = {
  'tshirt': '👕', 't-shirt': '👕',
  jacket: '🧥', pants: '👖',
  hoodie: '🧥', dress: '👗',
}

interface Props { garment: Garment }

export default function ProductCard({ garment }: Props) {
  const navigate = useNavigate()

  return (
    <div
      onClick={() => navigate(`/catalogue/${garment.id}`)}
      className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden cursor-pointer hover:shadow-md hover:-translate-y-0.5 transition-all"
    >
      <div className="h-40 bg-gradient-to-br from-brand-100 to-brand-50 flex items-center justify-center">
        <span className="text-5xl">{EMOJI[garment.category] ?? '👔'}</span>
      </div>
      <div className="p-4">
        <p className="text-xs font-semibold uppercase tracking-widest text-brand-500 mb-1">
          {garment.category}
        </p>
        <h3 className="font-semibold text-gray-800 text-sm leading-tight">{garment.name}</h3>
        <div className="flex gap-1 flex-wrap mt-2">
          {garment.sizes.slice(0, 4).map((s) => (
            <span key={s} className="text-xs px-1.5 py-0.5 bg-gray-100 rounded text-gray-500">
              {s}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
