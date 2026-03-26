import Link from 'next/link';
import { Product } from '@/lib/api';

interface ProductCardProps {
  product: Product;
}

const TYPE_LABELS: Record<string, string> = {
  top: 'Haut',
  bottom: 'Bas',
  dress: 'Robe',
  jacket: 'Veste',
};

export default function ProductCard({ product }: ProductCardProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden hover:shadow-md transition-shadow">
      <div className="aspect-square bg-gray-100 flex items-center justify-center">
        <div className="text-gray-300 text-6xl">👕</div>
      </div>

      <div className="p-4">
        <div className="flex items-start justify-between gap-2 mb-1">
          <h3 className="font-semibold text-gray-900 text-sm leading-tight">{product.name}</h3>
          <span className="text-indigo-600 font-bold text-sm whitespace-nowrap">
            {product.price.toFixed(2)} €
          </span>
        </div>

        <p className="text-xs text-gray-500 mb-1">{product.brand}</p>

        <span className="inline-block text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full mb-3">
          {TYPE_LABELS[product.type] ?? product.type}
        </span>

        <Link
          href={`/product/${product.id}`}
          className="block w-full text-center text-sm bg-indigo-600 hover:bg-indigo-700 text-white py-2 rounded-lg transition-colors"
        >
          Voir
        </Link>
      </div>
    </div>
  );
}
